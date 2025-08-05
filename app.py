# -*- coding: utf-8 -*-
# ====================================
# DFQ ZU EXCEL KONVERTER - FLASK ANWENDUNG
# Version 4.3 - Nutzt Original-Dateinamen für den Export
# ====================================

import os
import re
from datetime import datetime
import pandas as pd
import numpy as np
from flask import Flask, request, render_template, send_from_directory, url_for

# --- FLASK KONFIGURATION ---
app = Flask(__name__)
# Ordner für temporär erstellte Excel-Dateien
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER

# --- Q-DAS K-FELD DEFINITIONEN ---
K_FIELD_MAP = {
    'K0001': 'Werte', 'K0002': 'Attribut', 'K0004': 'Zeit/Datum', 'K0005': 'Ereignisse',
    'K0006': 'Chargennummer / Identnummer', 'K0007': 'Nestnummer / Spindelnummer',
    'K0008': 'Prüfer', 'K0009': 'Text / Messungs-Info', 'K0014': 'Teile Ident',
    'K0015': 'Untersuchungszweck', 'K0017': 'Prüfplanstatus', 'K0061': 'Katalog K0061',
    'K0100': 'Gesamtanzahl Merkmale', 'K1001': 'Teil Nummer', 'K1002': 'Teil Bezeichnung',
    'K1003': 'Teil Kurzbezeichnung', 'K1004': 'Änderungsstand Teil', 'K1010': 'Dokumentationspflicht',
    'K1021': 'Hersteller Nummer Text', 'K1022': 'Hersteller Name', 'K1041': 'Zeichnungsnummer',
    'K1042': 'Zeichnung Änderung', 'K1082': 'Maschine Bezeichnung', 'K1085': 'Maschine Standort',
    'K1086': 'Arbeitsgang / Operation', 'K1103': 'Kostenstelle', 'K1203': 'Prüfgrund', 'K1222': 'Prüfername',
    'K2001': 'Merkmal Nummer', 'K2002': 'Merkmal Bezeichnung', 'K2004': 'Merkmal Art',
    'K2005': 'Merkmal Klasse', 'K2006': 'Dokumentationspflicht', 'K2007': 'Regelungsart',
    'K2008': 'Gruppentyp', 'K2009': 'Messgröße', 'K2022': 'Nachkommastellen',
    'K2101': 'Nennmaß / Sollwert', 'K2110': 'Untere Spezifikationsgrenze (USG)',
    'K2111': 'Obere Spezifikationsgrenze (OSG)', 'K2112': 'Unteres Abmaß', 'K2113': 'Oberer Abmaß',
    'K2120': 'Art der Grenze unten', 'K2121': 'Art der Grenze oben', 'K2142': 'Einheit Bezeichnung',
    'K2152': 'Berechnete Toleranz', 'K2211': 'Normalnummer (Text)', 'K2212': 'Normalbezeichnung',
    'K2213': 'Normal Istwert', 'K2401': 'Prüfmittel Nummer Text', 'K2402': 'Prüfmittel Bezeichnung',
    'K2404': 'Prüfmittel Auflösung', 'K2410': 'Prüfort'
}

# --- PARSING-LOGIK (Unverändert) ---

def parse_dfq_data(content, logs):
    logs.append("📖 Starte Parsing gemäß Q-DAS Spezifikation...\n")
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    lines = [line for line in content.strip().split('\n') if line.strip()]

    header_lines, value_part_lines = [], []
    header_finished = False

    for i, line in enumerate(lines):
        is_header_k_field = line.strip().startswith(('K0100', 'K1', 'K2'))
        if not is_header_k_field and not header_finished:
            header_finished = True
        
        if header_finished: value_part_lines.append(line)
        else: header_lines.append(line)

    header_info, characteristics = {}, {}
    for line in header_lines: parse_k_code(line, header_info, characteristics)
    
    logs.append(f"   🔩 Header-Teil geparst: {len(header_info)} Felder.\n")
    logs.append(f"   🎯 Merkmals-Definitionen geladen: {len(characteristics)} Merkmale.\n")

    all_measurements, value_logs = parse_value_part(value_part_lines, characteristics)
    logs.extend(value_logs)
    
    if not all_measurements: return None

    return {
        'header_info': header_info,
        'characteristics': characteristics,
        'measurements': all_measurements
    }

def parse_k_code(line, info_dict, characteristics_dict):
    parts = line.strip().split(' ', 1)
    if len(parts) < 2: return
    code_part, value = parts[0], parts[1].strip()
    
    if '/' in code_part:
        base_code, index_str = code_part.split('/')
        if index_str.isdigit():
            index = int(index_str)
            if base_code.startswith('K2') and index > 0:
                if index not in characteristics_dict: characteristics_dict[index] = {}
                characteristics_dict[index][base_code] = value
            else:
                info_dict[code_part] = value
    else:
        info_dict[code_part] = value

def parse_value_part(lines, characteristics):
    logs = ["📖 Verarbeite Werteteil...\n"]
    all_measurements = []
    current_measurement_block = []
    
    for i, line in enumerate(lines):
        if not line.strip().startswith('K'):
            if current_measurement_block:
                process_measurement_block(current_measurement_block, characteristics, all_measurements, logs)
            current_measurement_block = [line]
        else:
            current_measurement_block.append(line)

    if current_measurement_block:
        process_measurement_block(current_measurement_block, characteristics, all_measurements, logs)

    logs.append(f"   ✅ Werteteil verarbeitet: {len(all_measurements)} Messpunkte gefunden.\n")
    return all_measurements, logs

def process_measurement_block(block_lines, characteristics, all_measurements, logs):
    if not block_lines: return
    measurement_line = block_lines[0]
    extra_k_lines = block_lines[1:]
    
    cleaned_line = measurement_line.replace('\x14', ' ').replace('#', ' ').replace('¤', ' ')
    groups = re.findall(r'(\d+[\.,]?\d*)\s+(\d+)\s+([\d\.\/\s]+[\d:]+)', cleaned_line)
    
    if groups:
        logs.append(f"    -> Zeile '{measurement_line[:40]}...' | Format 'Gruppen' erkannt.\n")
        timestamp = pd.to_datetime(groups[0][2].replace('/', ' '), dayfirst=True, errors='coerce')
        values = [(float(g[0].replace(',', '.')), int(g[1])) for g in groups]
    else:
        timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})', measurement_line)
        if timestamp_match:
            logs.append(f"    -> Zeile '{measurement_line[:40]}...' | Format 'Einzel-Zeitstempel' erkannt.\n")
            timestamp = pd.to_datetime(timestamp_match.group(1))
            raw_values = re.findall(r'(\d+[\.,]\d+)', measurement_line)
            values = [(float(v.replace(',', '.')), 0) for v in raw_values]
        else:
            logs.append(f"    -> Zeile '{measurement_line[:40]}...' | KEIN bekanntes Messformat. Ignoriert.\n")
            return

    extra_info = {}
    for k_line in extra_k_lines:
        parts = k_line.strip().split(' ', 1)
        if len(parts) == 2:
            extra_info[parts[0]] = parts[1]

    for i, (value, attr) in enumerate(values):
        char_index = i + 1
        char_name = characteristics.get(char_index, {}).get('K2002', f'Merkmal_{char_index}').strip()
        
        data_point = { 'Zeitstempel': timestamp, 'Merkmal': char_name, 'Wert': value, 'Attribut': attr }
        data_point.update(extra_info)
        all_measurements.append(data_point)

# --- EXCEL-ERSTELLUNG (ANGEPASST FÜR FLASK) ---
def create_excel_file(dfq_data, logs, original_filename): # <-- ÄNDERUNG HIER: original_filename hinzugefügt
    """Erstellt eine Excel-Datei und gibt den Dateinamen sowie Log-Meldungen zurück."""
    
    # --- ÄNDERUNG HIER: Dateiname wird aus dem Originalnamen abgeleitet ---
    base_filename, _ = os.path.splitext(original_filename)
    excel_filename = f"{base_filename}.xlsx"
    excel_filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], excel_filename)
    
    logs.append(f"\n💾 Erstelle Excel-Datei: {excel_filename}\n")

    try:
        df_measurements = pd.DataFrame(dfq_data['measurements'])
        index_cols = [col for col in df_measurements.columns if col not in ['Merkmal', 'Wert']]
        df_pivot = df_measurements.pivot_table(index=index_cols, columns='Merkmal', values='Wert').reset_index()
        
        renamed_columns = {col: K_FIELD_MAP.get(col.split('/')[0], col) for col in df_pivot.columns if col.startswith('K')}
        df_pivot.rename(columns=renamed_columns, inplace=True)

        logs.append(f"   📊 DataFrame erstellt: {df_pivot.shape[0]} Zeilen × {df_pivot.shape[1]} Spalten\n")

        with pd.ExcelWriter(excel_filepath, engine='openpyxl') as writer:
            df_pivot.to_excel(writer, sheet_name='Messwerte', index=False)
            logs.append("  ✅ Sheet 'Messwerte' erstellt\n")
            
            df_measurements.to_excel(writer, sheet_name='Rohdaten', index=False)
            logs.append("  ✅ Sheet 'Rohdaten' erstellt\n")
            
            numeric_pivot_cols = df_pivot.select_dtypes(include=np.number)
            if not numeric_pivot_cols.empty:
                stats_df = numeric_pivot_cols.describe()
                stats_df.to_excel(writer, sheet_name='Statistiken', index=True)
                logs.append("  ✅ Sheet 'Statistiken' erstellt\n")

            char_info_list = []
            for idx, char_data in sorted(dfq_data['characteristics'].items()):
                info = {'Index': idx}
                for code, value in char_data.items():
                    info[K_FIELD_MAP.get(code, code)] = value
                char_info_list.append(info)
            if char_info_list:
                pd.DataFrame(char_info_list).to_excel(writer, sheet_name='Merkmals-Info', index=False)
                logs.append("  ✅ Sheet 'Merkmals-Info' erstellt\n")

            header_info_list = []
            if dfq_data.get('header_info'):
                for code, value in dfq_data['header_info'].items():
                    description = K_FIELD_MAP.get(code.split('/')[0], code)
                    header_info_list.append({'Eigenschaft': description, 'K-Feld': code, 'Wert': value})
            if header_info_list:
                pd.DataFrame(header_info_list).to_excel(writer, sheet_name='Header-Info', index=False)
                logs.append("  ✅ Sheet 'Header-Info' erstellt\n")
        
        return excel_filename
        
    except Exception as e:
        logs.append(f"❌ Fehler beim Erstellen der Excel-Datei: {str(e)}\n")
        return None

# --- FLASK ROUTEN ---
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        logs = []
        if 'file' not in request.files:
            return render_template('index.html', error="Keine Datei im Request gefunden.")
        
        file = request.files['file']
        if file.filename == '':
            return render_template('index.html', error="Keine Datei ausgewählt.")

        if file and file.filename.endswith('.txt'):
            try:
                logs.append(f"🔧 Starte Konvertierung für Datei: {file.filename}\n")
                content = file.stream.read().decode("utf-8-sig")
                
                dfq_data = parse_dfq_data(content, logs)
                
                if not dfq_data:
                    return render_template('index.html', logs=logs, error="Keine gültigen Messdaten gefunden.")

                # --- ÄNDERUNG HIER: Der originale Dateiname wird übergeben ---
                excel_filename = create_excel_file(dfq_data, logs, file.filename)

                if excel_filename:
                    return render_template('index.html', logs=logs, download_file=excel_filename)
                else:
                    return render_template('index.html', logs=logs, error="Excel-Datei konnte nicht erstellt werden.")

            except Exception as e:
                return render_template('index.html', error=f"Ein unerwarteter Fehler ist aufgetreten: {e}")
        else:
            return render_template('index.html', error="Bitte laden Sie eine gültige .txt-Datei hoch.")

    return render_template('index.html')

@app.route('/download/<filename>')
def download_file(filename):
    """Stellt die generierte Datei zum Download bereit."""
    return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename, as_attachment=True)

# --- SKRIPT-AUSFÜHRUNG ---
if __name__ == '__main__':
    # host='0.0.0.0' macht die App im lokalen Netzwerk erreichbar
    app.run(debug=True, host='0.0.0.0')