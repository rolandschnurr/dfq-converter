# -*- coding: utf-8 -*-
"""
Q-DAS DFQ ZU EXCEL KONVERTER - ERWEITERTE VERSION 7.3 (DEBUG-MODUS)
Robuster Parser für verschiedene Q-DAS Formate
"""

import os
import re
import traceback
from datetime import datetime
import pandas as pd
import numpy as np
from flask import Flask, request, render_template, send_from_directory, jsonify
import zipfile
from io import BytesIO
from werkzeug.utils import secure_filename

# --- FLASK KONFIGURATION ---
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DOWNLOAD_FOLDER'] = 'downloads'

for folder in [app.config['UPLOAD_FOLDER'], app.config['DOWNLOAD_FOLDER']]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# --- ERWEITERTE Q-DAS K-FELD DEFINITIONEN ---
K_FIELD_MAP = {
    # Werteformate/Messwerte (K00xx)
    'K0001': 'Werte', 'K0002': 'Attribut', 'K0004': 'Zeit/Datum', 'K0005': 'Ereignisse',
    'K0006': 'Chargennummer/Identnummer', 'K0007': 'Nestnummer/Spindelnummer', 'K0008': 'Prüfer',
    'K0009': 'Text/Messungs-Info', 'K0010': 'Maschine', 'K0011': 'Prozessparameter',
    'K0012': 'Prüfmittel', 'K0014': 'Teile-Ident', 'K0015': 'Untersuchungszweck',
    'K0016': 'Produktionsnummer', 'K0017': 'Werkstückträgernummer', 'K0020': 'Stichprobenumfang',
    'K0021': 'Anzahl Fehler', 'K0053': 'Auftragsnummer', 'K0097': 'GUID',
    'K0100': 'Gesamtanzahl Merkmale', 'K0101': 'Anzahl Teile',
    
    # Teiledaten (K1xxx)
    'K1001': 'Teil-Nummer', 'K1002': 'Teil-Bezeichnung', 'K1003': 'Teil-Kurzbezeichnung',
    'K1004': 'Änderungsstand Teil', 'K1005': 'Erzeugnis', 'K1010': 'Dokumentationspflicht',
    'K1015': 'Untersuchungsart', 'K1017': 'Prüfplanstatus', 'K1041': 'Zeichnungsnummer',
    'K1042': 'Zeichnung-Änderung', 'K1081': 'Maschine-Nummer', 'K1082': 'Maschine-Bezeichnung',
    'K1085': 'Maschine-Standort', 'K1086': 'Arbeitsgang/Operation', 'K1100': 'Standort',
    'K1101': 'Abteilung', 'K1102': 'Arbeitsplatz', 'K1103': 'Kostenstelle',
    'K1203': 'Prüfgrund', 'K1204': 'Prüfdatum', 'K1206': 'Prüfauftragsnummer',
    'K1207': 'Prüfer-Info', 'K1222': 'Prüfername', 'K1997': 'GUID Teil', 'K1998': 'Zusatzdaten Teil',
    
    # Merkmalsdaten (K2xxx)
    'K2001': 'Merkmal-Nummer', 'K2002': 'Merkmal-Bezeichnung', 'K2004': 'Merkmal-Art',
    'K2005': 'Merkmal-Klasse', 'K2006': 'Dokumentationspflicht', 'K2007': 'Regelungsart',
    'K2008': 'Gruppentyp', 'K2009': 'Messgröße', 'K2011': 'Verteilungsart', 'K2013': 'Offset',
    'K2015': 'Art der Abnutzung', 'K2022': 'Nachkommastellen', 'K2023': 'Transformation Art',
    'K2024': 'Transformation Parameter a', 'K2025': 'Transformation Parameter b', 'K2026': 'Transformation Parameter c',
    'K2027': 'Transformation Parameter d', 'K2028': 'Natürliche Verteilung', 'K2041': 'Erfassungsart',
    'K2071': 'Additionskonstante', 'K2072': 'Multiplikationsfaktor', 'K2073': 'Maß des Einstellmeisters',
    'K2074': 'Aktueller Offset', 'K2075': 'Verstärkungsfaktor', 'K2080': 'Merkmalstatus',
    'K2100': 'Sollwert/Zielwert', 'K2101': 'Nennmaß/Sollwert', 'K2110': 'Untere Spezifikationsgrenze (USG)',
    'K2111': 'Obere Spezifikationsgrenze (OSG)', 'K2112': 'Unteres Abmaß', 'K2113': 'Oberes Abmaß',
    'K2120': 'Art der Grenze unten', 'K2121': 'Art der Grenze oben', 'K2135': 'Mittellage',
    'K2142': 'Einheit-Bezeichnung', 'K2144': 'Untere Warngrenze', 'K2145': 'Obere Warngrenze',
    'K2146': 'Warngrenze aktiv', 'K2152': 'Berechnete Toleranz', 'K2201': 'Auswertungstyp',
    'K2202': 'GC-Studie-Typ', 'K2203': 'GC-Studie Untertyp', 'K2205': 'Anzahl Teile',
    'K2211': 'Normal-Nummer', 'K2212': 'Normal-Bezeichnung', 'K2213': 'Normal-Istwert',
    'K2220': 'Anzahl Prüfer', 'K2221': 'Anzahl Messungen', 'K2222': 'Anzahl Referenzmessungen',
    'K2247': 'Zusatzdaten', 'K2303': 'Prüfer-Bezeichnung', 'K2312': 'Prozess-Bezeichnung',
    'K2401': 'Prüfmittel-Nummer', 'K2402': 'Prüfmittel-Bezeichnung', 'K2404': 'Prüfmittel-Auflösung',
    'K2406': 'Prüfmittel-Typ', 'K2411': 'Kalibrierdatum', 'K2601': 'Anzahl Dezimalstellen',
    'K2630': 'Messunsicherheit', 'K2640': 'MSA-Kennwert 1', 'K2641': 'MSA-Kennwert 2',
    'K2656': 'MSA-Status', 'K2900': 'Bemerkung', 'K2993': 'Status', 'K2996': 'Zusatzdaten 1',
    'K2997': 'GUID Merkmal', 'K2998': 'Zusatzdaten 2', 'K2999': 'Interne ID',
    
    # QRK-Daten (K8xxx)
    'K8010': 'Lagekarte Konfiguration', 'K8110': 'Streuungskarte Konfiguration', 'K8500': 'Stichprobenumfang',
    'K8501': 'Stichprobenart', 'K8503': 'Stichprobenart attributiv', 'K8504': 'Stichprobenintervall',
    'K8505': 'Stichprobengröße', 'K8530': 'Prozessstabilität', 'K8531': 'Cp-Wert',
    'K8532': 'Cpk-Wert', 'K8540': 'Bewertung'
}


def parse_dfq_data(content, logs, filename=""):
    """Parst Q-DAS DFQ-formatierte Daten mit Unterstützung für verschiedene Formate"""
    try:
        print(f"\n[DEBUG] === Starte Parsing für '{filename}' ===")
        logs.append(f"\n📖 Starte Parsing für '{filename}'...\n")
        
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        lines = content.strip().split('\n')
        
        if not lines:
            print("[DEBUG] FEHLER: Datei ist nach dem Einlesen leer.")
            logs.append(f"⚠️ Datei '{filename}' ist leer.\n")
            return None
        
        header_info, characteristics, measurements = parse_complete_file(lines, logs)
        
        print(f"[DEBUG] Parsing beendet. {len(measurements)} Messwert-Datensätze gefunden.")
        if not measurements:
            logs.append(f"⚠️ Keine Messwerte in '{filename}' gefunden.\n")
            return None
        
        logs.append(f"✅ Erfolgreich: {len(measurements)} Messwert-Datensätze gefunden.\n")
        
        return {
            'header_info': header_info,
            'characteristics': characteristics,
            'measurements': measurements,
            'filename': filename
        }
        
    except Exception as e:
        print(f"[DEBUG] FATALER FEHLER in parse_dfq_data: {str(e)}")
        print(traceback.format_exc())
        logs.append(f"❌ Fehler beim Parsing: {str(e)}\n{traceback.format_exc()}\n")
        return None

def parse_complete_file(lines, logs):
    """Parst die komplette Datei mit Header und Messwerten"""
    header_info = {}
    characteristics = {}
    measurements = []
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        print(f"[DEBUG] Zeile {i+1}/{len(lines)}: '{line[:120]}'")
        
        if not line:
            print("[DEBUG] --> Leere Zeile, übersprungen.")
            i += 1
            continue
        
        if line.startswith('K') and re.match(r'^K\d{4}', line[:5]):
            print("[DEBUG] --> Als K-Feld erkannt.")
            parse_k_field(line, header_info, characteristics)
            i += 1
        else:
            print("[DEBUG] --> Als Messwertzeile erkannt.")
            result = parse_measurement_line(line, characteristics)
            
            if result:
                print(f"[DEBUG] --> Parser fand {len(result)} Messung(en).")
                measurements.extend(result)
            else:
                print("[DEBUG] --> Parser fand keine gültigen Messungen in dieser Zeile.")
            i += 1
            
    print(f"[DEBUG] Schleife beendet. Merkmale gefunden: {characteristics}")
    logs.append(f"  📋 Header: {len(header_info)} Felder\n")
    logs.append(f"  🎯 Merkmale: {len(characteristics)} definiert\n")
    logs.append(f"  📊 Messungen: {len(measurements)} Werte-Datensätze\n")
    
    return header_info, characteristics, measurements

def parse_k_field(line, header_info, characteristics):
    """Parst K-Felder und speichert sie."""
    try:
        parts = line.split(' ', 1)
        if len(parts) < 2: return
        
        k_code, value = parts[0], parts[1].strip()
        header_info[k_code] = value
        
        if '/' in k_code:
            base_code, index_str = k_code.split('/', 1)
            if base_code.startswith('K2') and index_str.isdigit():
                idx = int(index_str)
                if idx not in characteristics: characteristics[idx] = {}
                characteristics[idx][base_code] = value
    except Exception as e:
        print(f"[DEBUG] FEHLER in parse_k_field: {e}")

def parse_measurement_line(line, characteristics):
    """Parst eine Messwertzeile iterativ und erkennt verschiedene Formate."""
    line = line.strip()
    if not line: return None

    print(f"  [PARSER] Versuch für Zeile: '{line[:120]}'")
    
    # --- VERSUCH 1: BOSCH-Format (hat Priorität, da es die ganze Zeile betrifft) ---
    bosch_pattern = re.compile(r'^\s*([-+]?\d*\.?\d+[Ee][+-]?\d+)\s+(\d+)\s+(.*)')
    match = bosch_pattern.match(line)
    if match:
        print("  [PARSER] --> BOSCH-Muster gefunden!")
        try:
            value_str, attr_str, rest = match.groups()
            merkmal_info = characteristics.get(1, {})
            merkmal_name = merkmal_info.get('K2002', merkmal_info.get('K2001', 'Messwert_1'))
            return [{'Wert': float(value_str), 'Attribut': int(attr_str), 'Zeitstempel': extract_timestamp(rest), 'Merkmal': merkmal_name}]
        except (ValueError, IndexError):
            print("  [PARSER] --> FEHLER bei Verarbeitung des BOSCH-Formats.")
            return None

    # --- VERSUCH 2: MESSDATE-Formate (iterativ) ---
    measurements = []
    current_pos = 0
    char_idx = 1
    # Ein flexibler Regex, der sowohl das Format mit Leerzeichen als auch das komprimierte findet
    messdate_pattern = re.compile(r'([-+]?\d+\.?\d*)\s*(\d+)\s*(\d{1,2}\.\d{1,2}\.\d{4}\/\d{1,2}:\d{1,2}:\d{1,2})')
    
    while current_pos < len(line):
        match = messdate_pattern.search(line, current_pos)
        if not match:
            # Wenn keine weiteren Treffer, Schleife beenden
            break
        
        print(f"  [PARSER] --> MESSDATE-Block gefunden an Position {match.start()}: {match.groups()}")
        
        try:
            value_str, attr_str, ts_str = match.groups()
            merkmal_info = characteristics.get(char_idx, {})
            merkmal_name = merkmal_info.get('K2002', merkmal_info.get('K2001', f'Merkmal_{char_idx}'))
            
            measurements.append({
                'Wert': float(value_str),
                'Attribut': int(attr_str),
                'Zeitstempel': extract_timestamp(ts_str),
                'Merkmal': merkmal_name
            })
            
            # Position für die nächste Suche aktualisieren
            current_pos = match.end()
            char_idx += 1
        except (ValueError, IndexError):
            # Wenn ein Block fehlerhaft ist, gehe zum nächsten
            current_pos = match.end()
            continue
            
    if measurements:
        return measurements
        
    print("  [PARSER] --> Kein bekanntes Format für diese Zeile gefunden.")
    return None

def extract_timestamp(text):
    """Extrahiert Zeitstempel aus Text."""
    patterns = [r'(\d{1,2}\.\d{1,2}\.\d{4}/\d{1,2}:\d{1,2}:\d{1,2})', r'(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})']
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try: return pd.to_datetime(match.group(1), dayfirst=True, errors='coerce')
            except Exception: continue
    return pd.NaT

def create_excel_file(dfq_data, output_filename=None):
    """Erstellt eine Excel-Datei aus geparsten DFQ-Daten"""
    print("\n[DEBUG] === Starte Excel-Erstellung ===")
    if not output_filename:
        base_name = os.path.splitext(dfq_data.get('filename', 'output'))[0]
        output_filename = f"{base_name}.xlsx"
    
    excel_buffer = BytesIO()
    
    try:
        df_measurements = pd.DataFrame(dfq_data['measurements'])
        print(f"[DEBUG] DataFrame aus {len(df_measurements)} Messungen erstellt.")
        print("[DEBUG] DataFrame Head:\n", df_measurements.head())
        
        if df_measurements.empty:
            print("[DEBUG] FEHLER: DataFrame ist leer, Excel wird nicht erstellt.")
            return None
        
        is_multi_feature = 'Merkmal' in df_measurements.columns and df_measurements['Merkmal'].nunique() > 1
        
        if is_multi_feature and df_measurements.duplicated(subset=['Zeitstempel']).any():
            try:
                # Füge Teil-Infos zum Index hinzu, um eindeutige Zeilen zu gewährleisten
                df_display = df_measurements.pivot_table(index=['Zeitstempel', 'Teil-Nr', 'Teil-Bez'], 
                                                        columns='Merkmal', values='Wert').reset_index()
                df_display.columns.name = None
                print("[DEBUG] --> DataFrame wurde erfolgreich pivotiert.")
            except Exception as e:
                print(f"[DEBUG] WARNUNG: Pivot-Tabelle fehlgeschlagen ({e}), verwende Rohdaten.")
                df_display = df_measurements
        else:
             df_display = df_measurements
             print("[DEBUG] --> DataFrame wird nicht pivotiert.")
        
        df_display = df_display.sort_values('Zeitstempel').round(6)
        
        with pd.ExcelWriter(excel_buffer, engine='openpyxl', datetime_format='DD.MM.YYYY HH:MM:SS') as writer:
            df_display.to_excel(writer, sheet_name='Messwerte', index=False)
            
            stats_df = df_display.describe(include=[np.number]).transpose().reset_index().rename(columns={'index': 'Merkmal'})
            stats_df.round(6).to_excel(writer, sheet_name='Statistiken', index=False)
            
            if dfq_data.get('characteristics'):
                char_rows = []
                for idx, char_info in sorted(dfq_data['characteristics'].items()):
                    row = {'Merkmal-Index': idx}
                    for k_code, value in char_info.items():
                        field_name = K_FIELD_MAP.get(k_code, k_code)
                        row[field_name] = value
                    char_rows.append(row)
                if char_rows: pd.DataFrame(char_rows).to_excel(writer, sheet_name='Merkmals-Info', index=False)
            
            if dfq_data.get('header_info'):
                header_rows = []
                for k_code, value in sorted(dfq_data['header_info'].items()):
                    base_code = k_code.split('/')[0]
                    field_name = K_FIELD_MAP.get(base_code, base_code)
                    header_rows.append({'K-Feld': k_code, 'Bezeichnung': field_name, 'Wert': value})
                if header_rows: pd.DataFrame(header_rows).to_excel(writer, sheet_name='Header-Info', index=False)
        
        excel_buffer.seek(0)
        print("[DEBUG] Excel-Erstellung erfolgreich abgeschlossen.")
        return excel_buffer
        
    except Exception as e:
        print(f"[DEBUG] FATALER FEHLER in create_excel_file: {str(e)}")
        print(traceback.format_exc())
        return None

# --- FLASK ROUTEN ---
# (Die Flask-Routen bleiben unverändert, sie sind nicht Teil des Parsing-Problems)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    logs = []
    print("\n\n[DEBUG] === Neue Upload-Anfrage erhalten ===")
    
    if 'files' not in request.files:
        print("[DEBUG] FEHLER: 'files' nicht in request.files gefunden.")
        return jsonify({'error': 'Keine Dateien hochgeladen'}), 400
    
    files = request.files.getlist('files')
    txt_files = [f for f in files if f.filename.lower().endswith('.txt')]
    
    if not txt_files:
        print("[DEBUG] FEHLER: Keine .txt-Dateien im Upload gefunden.")
        return jsonify({'error': 'Keine .txt Dateien gefunden'}), 400
    
    logs.append(f"🚀 Verarbeite {len(txt_files)} Datei(en)...\n")
    
    results = []
    for file in txt_files:
        try:
            filename = secure_filename(file.filename)
            content = file.read().decode('utf-8-sig', errors='ignore')
            
            dfq_data = parse_dfq_data(content, logs, filename)
            
            if dfq_data and dfq_data.get('measurements'):
                excel_buffer = create_excel_file(dfq_data)
                if excel_buffer:
                    excel_filename = os.path.splitext(filename)[0] + '.xlsx'
                    excel_path = os.path.join(app.config['DOWNLOAD_FOLDER'], excel_filename)
                    with open(excel_path, 'wb') as f: f.write(excel_buffer.getvalue())
                    results.append({'filename': filename, 'excel_filename': excel_filename, 'success': True})
                    logs.append(f"✅ '{filename}' erfolgreich konvertiert.\n")
                else:
                    logs.append(f"⚠️ Konnte keine Excel-Datei für '{filename}' erstellen.\n")
                    results.append({'filename': filename, 'success': False, 'error': 'Excel creation failed'})
            else:
                logs.append(f"⚠️ Keine Messdaten in '{filename}' gefunden oder Parsing fehlgeschlagen.\n")
                results.append({'filename': filename, 'success': False, 'error': 'No measurement data found'})

        except Exception as e:
            logs.append(f"❌ Schwerwiegender Fehler bei '{file.filename}': {str(e)}\n{traceback.format_exc()}")
            results.append({'filename': file.filename, 'success': False, 'error': str(e)})
    
    successful = [r for r in results if r.get('success')]
    
    if not successful:
        return jsonify({'error': 'Keine der Dateien konnte verarbeitet werden.', 'logs': "".join(logs)}), 400
    
    if len(successful) > 1:
        zip_filename = f"dfq_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = os.path.join(app.config['DOWNLOAD_FOLDER'], zip_filename)
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for result in successful:
                excel_path = os.path.join(app.config['DOWNLOAD_FOLDER'], result['excel_filename'])
                if os.path.exists(excel_path): zf.write(excel_path, result['excel_filename'])
        return jsonify({'success': True, 'download_url': f'/download/{zip_filename}', 'files_processed': len(successful), 'logs': "".join(logs)})
    
    elif len(successful) == 1:
        return jsonify({'success': True, 'download_url': f'/download/{successful[0]["excel_filename"]}', 'files_processed': 1, 'logs': "".join(logs)})
    
    return jsonify({'error': 'Unerwarteter Fehler nach der Verarbeitung.', 'logs': "".join(logs)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    print("="*60)
    print("Q-DAS DFQ zu Excel Konverter v7.3 (DEBUG-MODUS)")
    print("Optimiert für BOSCH- und MESSDATE-Formate")
    print("="*60)
    print(f"Server läuft auf: http://127.0.0.1:5000")
    print("Starte den Server und lade deine Dateien hoch.")
    print("Kopiere die gesamte Terminal-Ausgabe hierher, um den Fehler zu analysieren.")
    print("="*60)
    app.run(debug=True, host='0.0.0.0', port=5000)