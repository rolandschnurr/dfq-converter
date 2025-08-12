# excel_writer.py

"""
Modul zur Erstellung einer strukturierten Excel-Datei aus den geparsten Q-DAS-Daten.
"""
import pandas as pd
import numpy as np
import traceback
from io import BytesIO

def create_excel_file(dfq_data, k_field_map):
    """
    Erstellt eine Excel-Datei im Arbeitsspeicher aus den geparsten DFQ-Daten.

    Args:
        dfq_data (dict): Das Wörterbuch, das von qdas_parser.parse_dfq_data zurückgegeben wird.
        k_field_map (dict): Die geladenen K-Feld-Beschreibungen.

    Returns:
        BytesIO or None: Ein BytesIO-Objekt mit den Excel-Daten oder None bei einem Fehler.
    """
    excel_buffer = BytesIO()
    try:
        df_measurements = pd.DataFrame(dfq_data['measurements'])
        if df_measurements.empty:
            return None

        teil_nr = dfq_data['header_info'].get('K1001/1', dfq_data['header_info'].get('K1001', 'N/A'))
        teil_bez = dfq_data['header_info'].get('K1002/1', dfq_data['header_info'].get('K1002', 'N/A'))
        df_measurements['Teil-Nr'] = teil_nr
        df_measurements['Teil-Bez'] = teil_bez
        
        is_multi_feature_per_event = df_measurements.groupby('Event-ID')['Merkmal'].nunique().max() > 1
        
        if is_multi_feature_per_event:
            df_display = df_measurements.pivot_table(index=['Event-ID', 'Zeitstempel', 'Teil-Nr', 'Teil-Bez'], 
                                                     columns='Merkmal', values='Wert').reset_index()
            df_display.columns.name = None
            df_display = df_display.rename(columns={'Event-ID': 'Messung Nr.'})
        else:
            df_display = df_measurements.rename(columns={'Event-ID': 'Messung Nr.'})
        
        df_display = df_display.sort_values('Messung Nr.').round(6)
        
        with pd.ExcelWriter(excel_buffer, engine='openpyxl', datetime_format='YYYY-MM-DD HH:MM:SS') as writer:
            df_display.to_excel(writer, sheet_name='Messwerte', index=False)
            
            stats_df = df_display.describe(include=[np.number]).transpose().reset_index().rename(columns={'index': 'Merkmal'})
            stats_df.round(6).to_excel(writer, sheet_name='Statistiken', index=False)
            
            if dfq_data.get('characteristics'):
                char_rows = []
                for idx, char_info in sorted(dfq_data['characteristics'].items()):
                    row = {'Merkmal-Index': idx}
                    for k_code, value in char_info.items():
                        base_code = k_code.split('/')[0]
                        row[k_field_map.get(base_code, k_code)] = value
                    char_rows.append(row)
                if char_rows: pd.DataFrame(char_rows).to_excel(writer, sheet_name='Merkmals-Info', index=False)
            
            if dfq_data.get('header_info'):
                header_rows = [{'K-Feld': k, 'Bezeichnung': k_field_map.get(k.split('/')[0], k), 'Wert': v}
                               for k, v in sorted(dfq_data['header_info'].items())]
                if header_rows: pd.DataFrame(header_rows).to_excel(writer, sheet_name='Header-Info', index=False)
        
        excel_buffer.seek(0)
        return excel_buffer
        
    except Exception:
        print(f"[FEHLER] Bei der Excel-Erstellung: {traceback.format_exc()}")
        return None