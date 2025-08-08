# -*- coding: utf-8 -*-
"""
Q-DAS DFQ ZU EXCEL KONVERTER - ERWEITERTE VERSION
Version 5.0 - Verbesserte Robustheit und Batch-Verarbeitung
Unterstützt alle .txt Dateien im Q-DAS ASCII Transferformat
"""

import os
import re
import traceback
from datetime import datetime
import pandas as pd
import numpy as np
from flask import Flask, request, render_template, send_from_directory, jsonify, send_file
import zipfile
from io import BytesIO
from werkzeug.utils import secure_filename

# --- FLASK KONFIGURATION ---
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DOWNLOAD_FOLDER'] = 'downloads'

# Erstelle Verzeichnisse falls nicht vorhanden
for folder in [app.config['UPLOAD_FOLDER'], app.config['DOWNLOAD_FOLDER']]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# --- ERWEITERTE Q-DAS K-FELD DEFINITIONEN ---
K_FIELD_MAP = {
    # Werteformate/Messwerte (K00xx)
    'K0001': 'Werte',
    'K0002': 'Attribut',
    'K0004': 'Zeit/Datum',
    'K0005': 'Ereignisse',
    'K0006': 'Chargennummer/Identnummer',
    'K0007': 'Nestnummer/Spindelnummer',
    'K0008': 'Prüfer',
    'K0009': 'Text/Messungs-Info',
    'K0010': 'Maschine',
    'K0011': 'Prozessparameter',
    'K0012': 'Prüfmittel',
    'K0014': 'Teile-Ident',
    'K0015': 'Untersuchungszweck',
    'K0016': 'Produktionsnummer',
    'K0017': 'Werkstückträgernummer',
    'K0020': 'Stichprobenumfang',
    'K0021': 'Anzahl Fehler',
    'K0053': 'Auftragsnummer',
    'K0100': 'Gesamtanzahl Merkmale',
    
    # Teiledaten (K1xxx)
    'K1001': 'Teil-Nummer',
    'K1002': 'Teil-Bezeichnung',
    'K1003': 'Teil-Kurzbezeichnung',
    'K1004': 'Änderungsstand Teil',
    'K1010': 'Dokumentationspflicht',
    'K1015': 'Untersuchungsart',
    'K1017': 'Prüfplanstatus',
    'K1021': 'Hersteller-Nummer',
    'K1022': 'Hersteller-Name',
    'K1041': 'Zeichnungsnummer',
    'K1042': 'Zeichnung-Änderung',
    'K1081': 'Maschine-Nummer',
    'K1082': 'Maschine-Bezeichnung',
    'K1085': 'Maschine-Standort',
    'K1086': 'Arbeitsgang/Operation',
    'K1100': 'Standort',
    'K1101': 'Abteilung',
    'K1102': 'Arbeitsplatz',
    'K1103': 'Kostenstelle',
    'K1203': 'Prüfgrund',
    'K1204': 'Prüfdatum',
    'K1207': 'Prüfer-Info',
    'K1222': 'Prüfername',
    
    # Merkmalsdaten (K2xxx)
    'K2001': 'Merkmal-Nummer',
    'K2002': 'Merkmal-Bezeichnung',
    'K2004': 'Merkmal-Art',
    'K2005': 'Merkmal-Klasse',
    'K2006': 'Dokumentationspflicht',
    'K2007': 'Regelungsart',
    'K2008': 'Gruppentyp',
    'K2009': 'Messgröße',
    'K2011': 'Verteilungsart',
    'K2022': 'Nachkommastellen',
    'K2100': 'Sollwert/Zielwert',
    'K2101': 'Nennmaß/Sollwert',
    'K2110': 'Untere Spezifikationsgrenze (USG)',
    'K2111': 'Obere Spezifikationsgrenze (OSG)',
    'K2112': 'Unteres Abmaß',
    'K2113': 'Oberes Abmaß',
    'K2120': 'Art der Grenze unten',
    'K2121': 'Art der Grenze oben',
    'K2142': 'Einheit-Bezeichnung',
    'K2152': 'Berechnete Toleranz',
    'K2201': 'Auswerttyp',
    'K2202': 'GC-Studie-Typ',
    'K2205': 'Anzahl Teile',
    'K2220': 'Anzahl Prüfer',
    'K2221': 'Anzahl Messungen',
    'K2222': 'Anzahl Referenzmessungen',
    'K2302': 'Maschine-Bezeichnung',
    'K2303': 'Prüfer-Bezeichnung',
    'K2311': 'Fertigungsart',
    'K2401': 'Prüfmittel-Nummer',
    'K2402': 'Prüfmittel-Bezeichnung',
    'K2404': 'Prüfmittel-Auflösung',
    'K2410': 'Prüfort',
    
    # Strukturinformationen (K5xxx)
    'K5001': 'Strukturtyp',
    'K5002': 'Strukturbezeichnung',
    
    # QRK-Daten (K8xxx)
    'K8500': 'Stichprobenumfang',
    'K8501': 'Stichprobenart',
    'K8503': 'Stichprobenart-attributiv'
}

# --- VERBESSERTE PARSING-LOGIK ---

def parse_dfq_data(content, logs, filename=""):
    """Parst Q-DAS DFQ-formatierte Daten mit verbesserter Fehlerbehandlung"""
    try:
        logs.append(f"📖 Starte Parsing für '{filename}'...\n")
        
        # Normalisiere Zeilenenden
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        lines = [line for line in content.strip().split('\n') if line.strip()]
        
        if not lines:
            logs.append(f"⚠️ Datei '{filename}' ist leer oder enthält keine Daten.\n")
            return None
        
        # Trenne Header und Werteteil
        header_lines, value_part_lines = [], []
        header_finished = False
        
        for line in lines:
            # Erkenne Header-K-Felder
            is_header_k_field = bool(re.match(r'^K[0-9]{4}', line.strip()))
            
            # Wechsel zum Werteteil wenn keine K-Felder mehr kommen
            if not is_header_k_field and not header_finished and header_lines:
                header_finished = True
            
            if header_finished:
                value_part_lines.append(line)
            else:
                if is_header_k_field:
                    header_lines.append(line)
                elif header_lines:  # Wenn schon Header-Zeilen da sind
                    header_finished = True
                    value_part_lines.append(line)
        
        # Parse Header-Informationen
        header_info, characteristics = parse_header(header_lines, logs)
        
        # Validiere Pflichtfelder
        if not validate_required_fields(header_info, characteristics, logs):
            logs.append(f"⚠️ Datei '{filename}' fehlen Pflichtfelder.\n")
        
        # Parse Werteteil
        all_measurements = parse_value_part(value_part_lines, characteristics, logs)
        
        if not all_measurements:
            logs.append(f"⚠️ Keine gültigen Messwerte in '{filename}' gefunden.\n")
            return None
        
        logs.append(f"✅ Parsing von '{filename}' erfolgreich: {len(all_measurements)} Messwerte.\n")
        
        return {
            'header_info': header_info,
            'characteristics': characteristics,
            'measurements': all_measurements,
            'filename': filename
        }
        
    except Exception as e:
        logs.append(f"❌ Fehler beim Parsing von '{filename}': {str(e)}\n")
        return None

def parse_header(header_lines, logs):
    """Parst Header-Informationen mit verbesserter Merkmalserkennung"""
    header_info = {}
    characteristics = {}
    
    for line in header_lines:
        try:
            parts = line.strip().split(' ', 1)
            if len(parts) < 2:
                continue
                
            code_part, value = parts[0], parts[1].strip()
            
            # Behandle verschiedene K-Feld Formate
            if '/' in code_part:
                base_code, index_part = code_part.split('/', 1)
                
                # Format: Kxxxx/merkmal_index oder Kxxxx/0 (für alle Merkmale)
                if index_part.isdigit():
                    index = int(index_part)
                    
                    # Merkmalsspezifische Daten
                    if base_code.startswith('K2') and index > 0:
                        if index not in characteristics:
                            characteristics[index] = {}
                        
                        # Behandle mehrfache Werte mit Separator ¤
                        if '¤' in value:
                            values = value.split('¤')
                            for i, val in enumerate(values, 1):
                                if val.strip():
                                    if i not in characteristics:
                                        characteristics[i] = {}
                                    characteristics[i][base_code] = val.strip()
                        else:
                            characteristics[index][base_code] = value
                    else:
                        header_info[code_part] = value
                else:
                    # Andere Formate (z.B. K00xx/CharNr/...)
                    header_info[code_part] = value
            else:
                # Normale K-Felder ohne Index
                if code_part.startswith('K2') and '¤' in value:
                    # Mehrere Merkmale in einer Zeile
                    values = value.split('¤')
                    for i, val in enumerate(values, 1):
                        if val.strip():
                            if i not in characteristics:
                                characteristics[i] = {}
                            characteristics[i][code_part] = val.strip()
                else:
                    header_info[code_part] = value
                    
        except Exception as e:
            logs.append(f"  ⚠️ Fehler beim Parsen der Header-Zeile: {line[:50]}... - {str(e)}\n")
            continue
    
    logs.append(f"  📋 Header: {len(header_info)} Felder, {len(characteristics)} Merkmale definiert.\n")
    return header_info, characteristics

def validate_required_fields(header_info, characteristics, logs):
    """Validiert Pflichtfelder gemäß Q-DAS Spezifikation"""
    required_fields = {
        'K0100': 'Gesamtanzahl Merkmale',
        'K1001': 'Teilenummer',
        'K1002': 'Teilebezeichnung'
    }
    
    missing = []
    for field, name in required_fields.items():
        if field not in header_info:
            missing.append(f"{field} ({name})")
    
    # Prüfe ob Merkmale definiert sind
    if not characteristics:
        missing.append("Merkmalsdefinitionen (K2xxx)")
    
    if missing:
        logs.append(f"  ⚠️ Fehlende Pflichtfelder: {', '.join(missing)}\n")
        return False
    
    return True

def parse_value_part(lines, characteristics, logs):
    """Parst Werteteil mit verschiedenen Formaterkennungen"""
    all_measurements = []
    
    for line_num, line in enumerate(lines, 1):
        if not line.strip():
            continue
            
        # Überspringe K-Felder im Werteteil
        if line.strip().startswith('K'):
            # K-Felder im Werteteil können zusätzliche Informationen enthalten
            continue
        
        # Versuche verschiedene Parsing-Strategien
        measurements = parse_measurement_line(line, characteristics, line_num)
        if measurements:
            all_measurements.extend(measurements)
    
    return all_measurements

def parse_measurement_line(line, characteristics, line_num):
    """Parst eine einzelne Messwertezeile mit verschiedenen Formaterkennungen"""
    measurements = []
    
    try:
        # Bereinige die Zeile von Steuerzeichen
        cleaned_line = line
        for char in ['\x14', '\x0f', '¶', '¤']:
            cleaned_line = cleaned_line.replace(char, ' ')
        
        # Format 1: Wert Attribut Datum/Zeit Ereignis
        # Beispiel: 9.94 0 12.08.99/15:23:45 0
        pattern1 = r'([-+]?\d*\.?\d+)\s+(\d+)\s+([\d\.\/]+[\s\/][\d:]+)'
        matches = re.findall(pattern1, cleaned_line)
        
        if matches:
            # Extrahiere Zeitstempel vom ersten Match
            timestamp = None
            for match in matches:
                try:
                    date_str = match[2]
                    # Verschiedene Datumsformate unterstützen
                    for fmt in ['%d.%m.%y/%H:%M:%S', '%d.%m.%Y %H:%M:%S', 
                               '%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S']:
                        try:
                            timestamp = pd.to_datetime(date_str.replace('/', ' '), format=fmt)
                            break
                        except:
                            continue
                    if timestamp:
                        break
                except:
                    continue
            
            # Extrahiere alle Werte
            for i, match in enumerate(matches):
                try:
                    value = float(match[0])
                    attr = int(match[1])
                    
                    char_index = i + 1
                    char_name = characteristics.get(char_index, {}).get('K2002', f'Merkmal_{char_index}')
                    
                    measurements.append({
                        'Zeitstempel': timestamp if timestamp else pd.Timestamp.now(),
                        'Merkmal': char_name,
                        'Wert': value,
                        'Attribut': attr,
                        'Zeile': line_num
                    })
                except:
                    continue
        
        # Format 2: Nur numerische Werte (getrennt durch Leerzeichen oder Tabs)
        else:
            # Extrahiere alle numerischen Werte
            numeric_pattern = r'[-+]?\d*\.?\d+'
            values = re.findall(numeric_pattern, cleaned_line)
            
            if values:
                timestamp = pd.Timestamp.now()
                for i, val_str in enumerate(values):
                    try:
                        value = float(val_str)
                        char_index = i + 1
                        char_name = characteristics.get(char_index, {}).get('K2002', f'Merkmal_{char_index}')
                        
                        measurements.append({
                            'Zeitstempel': timestamp,
                            'Merkmal': char_name,
                            'Wert': value,
                            'Attribut': 0,  # Standard: gültiger Wert
                            'Zeile': line_num
                        })
                    except:
                        continue
    
    except Exception as e:
        # Fehler still behandeln, da nicht alle Zeilen Messwerte enthalten müssen
        pass
    
    return measurements

# --- EXCEL-ERSTELLUNG ---

def create_excel_file(dfq_data, output_filename=None):
    """Erstellt eine Excel-Datei aus geparsten DFQ-Daten"""
    
    if not output_filename:
        base_name = os.path.splitext(dfq_data.get('filename', 'output'))[0]
        output_filename = f"{base_name}.xlsx"
    
    # Erstelle temporäre Datei im Memory
    excel_buffer = BytesIO()
    
    try:
        # Konvertiere Messungen zu DataFrame
        df_measurements = pd.DataFrame(dfq_data['measurements'])
        
        if df_measurements.empty:
            return None
        
        # Erstelle Pivot-Tabelle für bessere Übersicht
        pivot_df = None
        if 'Merkmal' in df_measurements.columns and 'Wert' in df_measurements.columns:
            index_cols = [col for col in df_measurements.columns 
                         if col not in ['Merkmal', 'Wert']]
            if index_cols:
                try:
                    pivot_df = df_measurements.pivot_table(
                        index=index_cols, 
                        columns='Merkmal', 
                        values='Wert',
                        aggfunc='first'
                    ).reset_index()
                except:
                    pass
        
        # Schreibe Excel-Datei
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            # Sheet 1: Pivot-Ansicht (wenn möglich)
            if pivot_df is not None and not pivot_df.empty:
                pivot_df.to_excel(writer, sheet_name='Messwerte', index=False)
            
            # Sheet 2: Rohdaten
            df_measurements.to_excel(writer, sheet_name='Rohdaten', index=False)
            
            # Sheet 3: Statistiken
            if pivot_df is not None:
                numeric_cols = pivot_df.select_dtypes(include=np.number)
                if not numeric_cols.empty:
                    stats_df = numeric_cols.describe()
                    stats_df.to_excel(writer, sheet_name='Statistiken')
            
            # Sheet 4: Merkmalsinformationen
            if dfq_data.get('characteristics'):
                char_data = []
                for idx, char_info in dfq_data['characteristics'].items():
                    row = {'Merkmal-Index': idx}
                    for code, value in char_info.items():
                        field_name = K_FIELD_MAP.get(code, code)
                        row[field_name] = value
                    char_data.append(row)
                
                if char_data:
                    pd.DataFrame(char_data).to_excel(
                        writer, sheet_name='Merkmals-Info', index=False
                    )
            
            # Sheet 5: Header-Informationen
            if dfq_data.get('header_info'):
                header_data = []
                for code, value in dfq_data['header_info'].items():
                    field_name = K_FIELD_MAP.get(code.split('/')[0], code)
                    header_data.append({
                        'K-Feld': code,
                        'Bezeichnung': field_name,
                        'Wert': value
                    })
                
                if header_data:
                    pd.DataFrame(header_data).to_excel(
                        writer, sheet_name='Header-Info', index=False
                    )
        
        excel_buffer.seek(0)
        return excel_buffer
        
    except Exception as e:
        print(f"Fehler beim Erstellen der Excel-Datei: {str(e)}")
        return None

# --- BATCH-VERARBEITUNG ---

def process_multiple_files(files, logs):
    """Verarbeitet mehrere DFQ-Dateien"""
    results = []
    
    for file in files:
        try:
            filename = secure_filename(file.filename)
            logs.append(f"\n{'='*50}\n")
            logs.append(f"📁 Verarbeite Datei: {filename}\n")
            
            # Lese Dateiinhalt
            content = file.read().decode('utf-8-sig', errors='ignore')
            
            # Parse DFQ-Daten
            dfq_data = parse_dfq_data(content, logs, filename)
            
            if dfq_data:
                # Erstelle Excel-Datei
                excel_buffer = create_excel_file(dfq_data)
                if excel_buffer:
                    results.append({
                        'filename': filename,
                        'excel_buffer': excel_buffer,
                        'success': True
                    })
                    logs.append(f"✅ Excel-Datei für '{filename}' erfolgreich erstellt.\n")
                else:
                    results.append({
                        'filename': filename,
                        'success': False,
                        'error': 'Excel-Erstellung fehlgeschlagen'
                    })
            else:
                results.append({
                    'filename': filename,
                    'success': False,
                    'error': 'Parsing fehlgeschlagen'
                })
                
        except Exception as e:
            logs.append(f"❌ Fehler bei '{file.filename}': {str(e)}\n")
            results.append({
                'filename': file.filename,
                'success': False,
                'error': str(e)
            })
    
    return results

# --- FLASK ROUTEN ---

@app.route('/')
def index():
    """Hauptseite"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """Verarbeitet hochgeladene Dateien"""
    logs = []
    
    if 'files' not in request.files:
        return jsonify({'error': 'Keine Dateien hochgeladen'}), 400
    
    files = request.files.getlist('files')
    
    # Filtere nur .txt Dateien
    txt_files = [f for f in files if f.filename.endswith('.txt')]
    
    if not txt_files:
        return jsonify({'error': 'Keine .txt Dateien gefunden'}), 400
    
    logs.append(f"🚀 Starte Verarbeitung von {len(txt_files)} Dateien...\n")
    
    # Verarbeite Dateien
    results = process_multiple_files(txt_files, logs)
    
    # Zähle erfolgreiche Verarbeitungen
    successful = [r for r in results if r['success']]
    
    if not successful:
        return jsonify({
            'error': 'Keine Dateien konnten erfolgreich verarbeitet werden',
            'logs': logs
        }), 400
    
    # Erstelle ZIP-Datei mit allen Excel-Dateien
    if len(successful) > 1:
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for result in successful:
                excel_name = os.path.splitext(result['filename'])[0] + '.xlsx'
                zip_file.writestr(excel_name, result['excel_buffer'].getvalue())
        
        zip_buffer.seek(0)
        
        # Speichere ZIP temporär
        zip_filename = f"dfq_excel_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = os.path.join(app.config['DOWNLOAD_FOLDER'], zip_filename)
        with open(zip_path, 'wb') as f:
            f.write(zip_buffer.getvalue())
        
        return jsonify({
            'success': True,
            'download_url': f'/download/{zip_filename}',
            'files_processed': len(successful),
            'logs': logs
        })
    
    # Einzelne Datei
    elif len(successful) == 1:
        result = successful[0]
        excel_name = os.path.splitext(result['filename'])[0] + '.xlsx'
        excel_path = os.path.join(app.config['DOWNLOAD_FOLDER'], excel_name)
        
        with open(excel_path, 'wb') as f:
            f.write(result['excel_buffer'].getvalue())
        
        return jsonify({
            'success': True,
            'download_url': f'/download/{excel_name}',
            'files_processed': 1,
            'logs': logs
        })

@app.route('/download/<filename>')
def download_file(filename):
    """Download-Route für generierte Dateien"""
    return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename, as_attachment=True)

# --- HAUPTPROGRAMM ---

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)