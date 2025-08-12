# main.py

# -*- coding: utf-8 -*-
"""
Q-DAS DFQ ZU EXCEL KONVERTER - FINALE STABILE VERSION
"""
import os
import traceback
import zipfile
from datetime import datetime
from flask import Flask, request, render_template, send_from_directory, jsonify
from werkzeug.utils import secure_filename

import config
import k_fields_loader
import qdas_parser
import excel_writer

# === FLASK APP INITIALISIERUNG ===
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
app.config['DOWNLOAD_FOLDER'] = config.DOWNLOAD_FOLDER

K_FIELD_MAP = k_fields_loader.load_k_field_map(config.K_FIELD_DEFINITION_FILE)

for folder in [app.config['UPLOAD_FOLDER'], app.config['DOWNLOAD_FOLDER']]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# === FLASK ROUTEN ===
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
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
        filename = secure_filename(file.filename)
        try:
            content_as_string = file.read().decode('utf-8-sig', errors='ignore')
			dfq_data = qdas_parser.parse_dfq_data(content_as_string, logs, filename)
            
            if dfq_data:
                excel_buffer = excel_writer.create_excel_file(dfq_data, K_FIELD_MAP)
                if excel_buffer:
                    excel_filename = os.path.splitext(filename)[0] + '.xlsx'
                    excel_path = os.path.join(app.config['DOWNLOAD_FOLDER'], excel_filename)
                    with open(excel_path, 'wb') as f: f.write(excel_buffer.getvalue())
                    results.append({'filename': filename, 'excel_filename': excel_filename, 'success': True})
                else:
                    results.append({'filename': filename, 'success': False})
            else:
                results.append({'filename': filename, 'success': False})

        except Exception as e:
            logs.append(f"❌ Schwerwiegender Fehler bei '{filename}': {str(e)}\n{traceback.format_exc()}")
            results.append({'filename': filename, 'success': False})
    
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
        return jsonify({'success': True, 'download_url': f'/download/{zip_filename}'})
    else:
        return jsonify({'success': True, 'download_url': f'/download/{successful[0]["excel_filename"]}'})

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename, as_attachment=True)

# === HAUPTAUSFÜHRUNGSBLOCK ===
if __name__ == '__main__':
    print("="*60)
    print("Q-DAS Konverter - Finale Stabile Version")
    print(f"Server läuft auf: http://12c7.0.0.1:5000")
    print("="*60)
    app.run(debug=False, host='0.0.0.0', port=5000)