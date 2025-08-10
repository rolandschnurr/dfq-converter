# -*- coding: utf-8 -*-
"""
Q-DAS DFQ ZU EXCEL KONVERTER - VERSION 9.0 (Clean Code)

Ein Flask-Webserver zur Konvertierung von Q-DAS ASCII-Transferformat-Dateien (.txt)
in Excel-Dateien (.xlsx).

Unterstützt verschiedene Q-DAS-Dialekte, darunter:
- BOSCH-Format (wissenschaftliche Notation, eine Messung pro Zeile, gefolgt von K0097 GUID)
- MESSDATE-Format (mehrere Messungen pro Zeile, getrennt durch Leerzeichen)
- MESSDATE-Format mit DC4-Steuerzeichen (\x14) als Trenner

Die K-Feld-Definitionen werden aus einer externen Datei (k_fields.txt) geladen,
um die Wartbarkeit zu erhöhen.
"""

# ==============================================================================
# 1. IMPORTS
# ==============================================================================
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

# ==============================================================================
# 2. FLASK APP KONFIGURATION
# ==============================================================================
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB max upload size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DOWNLOAD_FOLDER'] = 'downloads'
K_FIELD_DEFINITION_FILE = "k_fields.txt"

# Erstelle notwendige Ordner, falls sie nicht existieren
for folder in [app.config['UPLOAD_FOLDER'], app.config['DOWNLOAD_FOLDER']]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# ==============================================================================
# 3. KONFIGURATIONS-LADEFUNKTION
# ==============================================================================
def load_k_field_map(filepath):
    """
    Lädt die K-Feld-Definitionen aus einer externen Textdatei im Format 'KEY = WERT'.

    Args:
        filepath (str): Der Pfad zur Definitionsdatei.

    Returns:
        dict: Ein Wörterbuch mit den K-Feld-Definitionen.
    """
    k_map = {}
    print(f"[INFO] Lade K-Feld Definitionen aus '{filepath}'...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Ignore comments and empty lines
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    k_map[key.strip()] = value.strip()
    except FileNotFoundError:
        print(f"[WARNUNG] Definitionsdatei '{filepath}' nicht gefunden. K-Feld-Bezeichnungen werden fehlen.")
    
    print(f"[INFO] {len(k_map)} K-Feld Definitionen erfolgreich geladen.")
    return k_map

# Globale Variable für die K-Feld-Definitionen, wird beim Start geladen
K_FIELD_MAP = load_k_field_map(K_FIELD_DEFINITION_FILE)

# ==============================================================================
# 4. CORE PARSING LOGIC
# ==============================================================================
def parse_dfq_data(content, logs, filename=""):
    """
    Hauptfunktion, die den gesamten Parsing-Prozess für eine Datei steuert.

    Args:
        content (str): Der Inhalt der hochgeladenen Datei als String.
        logs (list): Eine Liste zur Sammlung von Log-Nachrichten für das Frontend.
        filename (str): Der Name der Datei für die Log-Ausgaben.

    Returns:
        dict or None: Ein Wörterbuch mit den geparsten Daten oder None bei einem Fehler.
    """
    try:
        logs.append(f"\n📖 Starte Parsing für '{filename}'...\n")
        
        # Normalize line endings
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        lines = content.strip().split('\n')
        
        if not lines:
            logs.append(f"⚠️ Datei '{filename}' ist leer.\n")
            return None
        
        header_info, characteristics, measurements = parse_file_content(lines, logs)
        
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
    except Exception:
        logs.append(f"❌ Ein unerwarteter Fehler ist beim Parsen aufgetreten: {traceback.format_exc()}\n")
        return None

def parse_file_content(lines, logs):
    """
    Iteriert durch die Zeilen einer Datei und leitet sie an den K-Feld-
    oder Messwert-Parser weiter.

    Args:
        lines (list): Die Zeilen der Datei.
        logs (list): Eine Liste zur Sammlung von Log-Nachrichten.

    Returns:
        tuple: Enthält header_info, characteristics und measurements.
    """
    header_info = {}
    characteristics = {}
    measurements = []
    measurement_event_id = 1  # Eindeutiger Zähler für jede Messwert-Zeile

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        
        # K0097 (GUID) gehört zur vorherigen Messung und wird speziell behandelt
        if line.startswith('K0097'):
            if measurements:
                parts = line.split(' ', 1)
                if len(parts) > 1:
                    measurements[-1]['GUID'] = parts[1].strip()
            i += 1
            continue

        # Standard-K-Feld
        if line.startswith('K') and re.match(r'^K\d{4}', line[:5]):
            parse_k_field(line, header_info, characteristics)
            i += 1
        # Alles andere ist potenziell eine Messwertzeile
        else:
            result = parse_measurement_line(line, characteristics, measurement_event_id)
            if result:
                measurements.extend(result)
                measurement_event_id += 1
            i += 1
            
    return header_info, characteristics, measurements

def parse_k_field(line, header_info, characteristics):
    """
    Parst eine einzelne K-Feld-Zeile und ordnet sie entweder den allgemeinen
    Header-Informationen oder den spezifischen Merkmalen zu.

    Args:
        line (str): Die zu parsende Zeile.
        header_info (dict): Wörterbuch für allgemeine Header-Daten.
        characteristics (dict): Wörterbuch für merkmalsbezogene Daten.
    """
    try:
        parts = line.split(' ', 1)
        if len(parts) < 2: return
        
        k_code_full, value = parts[0], parts[1].strip()
        
        # Speichere jedes K-Feld im Header für eine vollständige Referenz
        header_info[k_code_full] = value
        
        # Behandle indexierte Felder (z.B. K2001/1)
        if '/' in k_code_full:
            base_code, index_str = k_code_full.split('/', 1)
            # Nur K2xxx-Felder gehören zu den 'characteristics'
            if base_code.startswith('K2') and index_str.isdigit():
                idx = int(index_str)
                if idx not in characteristics: characteristics[idx] = {}
                characteristics[idx][base_code] = value
    except Exception:
        # Fehler leise ignorieren, um den Prozess nicht zu stoppen
        pass

def parse_measurement_line(line, characteristics, event_id):
    """
    Parst eine einzelne Messwertzeile. Erkennt automatisch verschiedene Formate.
    Gibt eine Liste von Messwert-Wörterbüchern zurück.

    Args:
        line (str): Die Messwertzeile.
        characteristics (dict): Die zuvor geparsten Merkmalsdefinitionen.
        event_id (int): Eine eindeutige ID für diese Zeile, um Duplikate zu vermeiden.

    Returns:
        list or None: Eine Liste von Messungen oder None, wenn kein Format passt.
    """
    # HINWEIS: DC4-Steuerzeichen (\x14)
    # Einige Q-DAS-Systeme verwenden dieses nicht-druckbare Zeichen anstelle 
    # eines Leerzeichens als Trenner. Der Regex berücksichtigt beides.
    messdate_pattern = re.compile(
        r'([-+]?\d+\.?\d*)'                                    # Gruppe 1: Der Messwert
        r'[\s\x14]+'                                           # Trenner: Whitespace ODER DC4
        r'(\d+)'                                               # Gruppe 2: Das Attribut
        r'[\s\x14]+'                                           # Trenner: Whitespace ODER DC4
        r'(\d{1,2}\.\d{1,2}\.\d{4}\/\d{1,2}:\d{1,2}:\d{1,2})' # Gruppe 3: Das Datum
    )
    matches = messdate_pattern.findall(line)
    if matches:
        measurements = []
        for i, match_tuple in enumerate(matches):
            try:
                char_idx = i + 1
                value_str, attr_str, ts_str = match_tuple
                merkmal_info = characteristics.get(char_idx, {})
                merkmal_name = merkmal_info.get('K2002', merkmal_info.get('K2001', f'Merkmal_{char_idx}'))
                
                measurements.append({
                    'Event-ID': event_id, 'Wert': float(value_str), 'Attribut': int(attr_str),
                    'Zeitstempel': extract_timestamp(ts_str), 'Merkmal': merkmal_name
                })
            except (ValueError, IndexError):
                continue
        if measurements:
            return measurements

    # Fallback-Parser für BOSCH-Format
    bosch_pattern = re.compile(r'^\s*([-+]?\d*\.?\d+[Ee][+-]?\d+)\s+(\d+)\s+(.*)')
    match = bosch_pattern.match(line)
    if match:
        try:
            value_str, attr_str, rest = match.groups()
            merkmal_info = characteristics.get(1, {}) # BOSCH-Format hat oft nur ein Merkmal pro Datei
            merkmal_name = merkmal_info.get('K2002/1', merkmal_info.get('K2002', 'N/A'))
            return [{'Event-ID': event_id, 'Wert': float(value_str), 'Attribut': int(attr_str), 'Zeitstempel': extract_timestamp(rest), 'Merkmal': merkmal_name}]
        except (ValueError, IndexError):
            return None
            
    return None

def extract_timestamp(text):
    """Extrahiert ein Datum aus einem Text-String und gibt ein Pandas-Timestamp-Objekt zurück."""
    try:
        # Pandas ist sehr gut darin, verschiedene Datumsformate automatisch zu erkennen
        return pd.to_datetime(text, dayfirst=True, errors='coerce')
    except Exception:
        return pd.NaT

# ==============================================================================
# 5. EXCEL EXPORT LOGIC
# ==============================================================================
def create_excel_file(dfq_data):
    """
    Erstellt eine Excel-Datei im Speicher aus den geparsten DFQ-Daten.

    Args:
        dfq_data (dict): Das Wörterbuch, das von parse_dfq_data zurückgegeben wird.

    Returns:
        BytesIO or None: Ein BytesIO-Objekt mit den Excel-Daten oder None bei einem Fehler.
    """
    excel_buffer = BytesIO()
    try:
        df_measurements = pd.DataFrame(dfq_data['measurements'])
        if df_measurements.empty:
            return None

        # Füge Teil-Informationen hinzu, bevor weiterverarbeitet wird
        teil_nr = dfq_data['header_info'].get('K1001/1', dfq_data['header_info'].get('K1001', 'N/A'))
        teil_bez = dfq_data['header_info'].get('K1002/1', dfq_data['header_info'].get('K1002', 'N/A'))
        df_measurements['Teil-Nr'] = teil_nr
        df_measurements['Teil-Bez'] = teil_bez
        
        # Entscheide, ob eine Pivot-Tabelle sinnvoll ist.
        # Dies ist der Fall, wenn eine Messwertzeile (identifiziert durch Event-ID)
        # Daten für mehrere verschiedene Merkmale enthält.
        is_multi_feature_per_event = df_measurements.groupby('Event-ID')['Merkmal'].nunique().max() > 1
        
        if is_multi_feature_per_event:
            df_display = df_measurements.pivot_table(index=['Event-ID', 'Zeitstempel', 'Teil-Nr', 'Teil-Bez'], 
                                                     columns='Merkmal', values='Wert').reset_index()
            df_display.columns.name = None
            df_display = df_display.rename(columns={'Event-ID': 'Messung Nr.'})
        else:
            # Für Formate wie BOSCH ist kein Pivot nötig
            df_display = df_measurements.rename(columns={'Event-ID': 'Messung Nr.'})
        
        df_display = df_display.sort_values('Messung Nr.').round(6)
        
        # Schreibe die Daten in verschiedene Excel-Sheets
        with pd.ExcelWriter(excel_buffer, engine='openpyxl', datetime_format='YYYY-MM-DD HH:MM:SS') as writer:
            # Sheet 1: Messwerte
            df_display.to_excel(writer, sheet_name='Messwerte', index=False)
            
            # Sheet 2: Statistiken
            stats_df = df_display.describe(include=[np.number]).transpose().reset_index().rename(columns={'index': 'Merkmal'})
            stats_df.round(6).to_excel(writer, sheet_name='Statistiken', index=False)
            
            # Sheet 3: Merkmals-Info
            if dfq_data.get('characteristics'):
                char_rows = []
                for idx, char_info in sorted(dfq_data['characteristics'].items()):
                    row = {'Merkmal-Index': idx}
                    for k_code, value in char_info.items():
                        base_code = k_code.split('/')[0]
                        row[K_FIELD_MAP.get(base_code, k_code)] = value
                    char_rows.append(row)
                if char_rows: pd.DataFrame(char_rows).to_excel(writer, sheet_name='Merkmals-Info', index=False)
            
            # Sheet 4: Header-Info
            if dfq_data.get('header_info'):
                header_rows = [{'K-Feld': k, 'Bezeichnung': K_FIELD_MAP.get(k.split('/')[0], k), 'Wert': v}
                               for k, v in sorted(dfq_data['header_info'].items())]
                if header_rows: pd.DataFrame(header_rows).to_excel(writer, sheet_name='Header-Info', index=False)
        
        excel_buffer.seek(0)
        return excel_buffer
        
    except Exception:
        print(f"[FEHLER] Bei der Excel-Erstellung: {traceback.format_exc()}")
        return None

# ==============================================================================
# 6. WEB SERVER LOGIC (FLASK)
# ==============================================================================
@app.route('/')
def index():
    """Zeigt die Hauptseite mit dem Upload-Formular an."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """Verarbeitet die hochgeladenen Dateien."""
    logs = []
    if 'files' not in request.files:
        return jsonify({'error': 'Keine Dateien hochgeladen'}), 400
    
    files = request.files.getlist('files')
    txt_files = [f for f in files if f.filename.lower().endswith('.txt')]
    
    if not txt_files:
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
        return jsonify({'error': 'Keine der Dateien konnte verarbeitet werden.', 'logs': logs}), 400
    
    if len(successful) > 1:
        zip_filename = f"dfq_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = os.path.join(app.config['DOWNLOAD_FOLDER'], zip_filename)
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for result in successful:
                excel_path = os.path.join(app.config['DOWNLOAD_FOLDER'], result['excel_filename'])
                if os.path.exists(excel_path): zf.write(excel_path, result['excel_filename'])
        return jsonify({'success': True, 'download_url': f'/download/{zip_filename}', 'files_processed': len(successful), 'logs': logs})
    
    elif len(successful) == 1:
        return jsonify({'success': True, 'download_url': f'/download/{successful[0]["excel_filename"]}', 'files_processed': 1, 'logs': logs})
    
    return jsonify({'error': 'Unerwarteter Fehler nach der Verarbeitung.', 'logs': logs}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Stellt die generierte Datei zum Download bereit."""
    return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename, as_attachment=True)

# ==============================================================================
# 7. HAUPTAUSFÜHRUNGSBLOCK
# ==============================================================================
if __name__ == '__main__':
    print("="*60)
    print("Q-DAS DFQ zu Excel Konverter v9.0 (Clean Code)")
    print(f"Server läuft auf: http://127.0.0.1:5000")
    print("="*60)
    app.run(debug=False, host='0.0.0.0', port=5000)