# qdas_parser.py

"""
Haupt-Parsing-Modul, das den Prozess orchestriert.
Diese Datei enthält selbst KEINE Parsing-Logik mehr, sondern delegiert
an die Spezialisten aus dem 'parsers'-Paket.
"""
import re
import traceback

# Importiert die definierte Kette von Parser-Funktionen aus dem parsers-Paket.
from parsers import PARSER_CHAIN

def _parse_measurement_line(line, characteristics, event_id, logs):
    """
    Iteriert durch die Kette der verfügbaren Parser und gibt das Ergebnis
    des ersten erfolgreichen Parsers zurück.
    """
    for parser_func in PARSER_CHAIN:
        try:
            # Ruft die 'parse'-Funktion aus bosch_parser.py oder messdate_parser.py auf.
            result = parser_func(line, characteristics, event_id, logs)
            if result:
                return result
        except Exception as e:
            # Fängt nur einen kompletten Absturz eines Parsers ab.
            logs.append(f"FATALER ABSTURZ im Parser '{parser_func.__name__}': {e}\n{traceback.format_exc()}")
    return None

def _parse_k_field(line, header_info, characteristics):
    """Parst eine einzelne K-Feld-Zeile."""
    try:
        parts = line.split(' ', 1)
        if len(parts) < 2: return
        k_code_full, value = parts[0], parts[1].strip()
        header_info[k_code_full] = value
        if '/' in k_code_full:
            base_code, index_str = k_code_full.split('/', 1)
            if base_code.startswith('K2') and index_str.isdigit():
                idx = int(index_str)
                if idx not in characteristics: characteristics[idx] = {}
                characteristics[idx][base_code] = value
    except:
        pass

def _parse_file_content(lines, logs):
    """Loop durch alle Zeilen der Datei und delegiert die Verarbeitung."""
    header_info, characteristics, measurements = {}, {}, []
    measurement_event_id = 1
    for i, line in enumerate(lines):
        line = line.strip()
        if not line: continue

        if line.startswith('K0097/'):
            if measurements:
                parts = line.split(' ', 1)
                if len(parts) > 1: measurements[-1]['GUID'] = parts[1].strip()
            continue

        if line.startswith('K') and re.match(r'^K\d{4}', line[:5]):
            _parse_k_field(line, header_info, characteristics)
            continue
        
        result = _parse_measurement_line(line, characteristics, measurement_event_id, logs)
        if result:
            measurements.extend(result)
            measurement_event_id += 1

    return header_info, characteristics, measurements

def parse_dfq_data(content_as_string, logs, filename=""):
    """
    Haupt-Einstiegspunkt für das Parsing. Empfängt einen sauberen String.
    """
    try:
        logs.append(f"\n📖 Starte Parsing für '{filename}'...\n")
        # .splitlines() ist die robusteste Methode, einen String in Zeilen zu teilen.
        lines = content_as_string.splitlines()
        
        if not lines:
            logs.append(f"⚠️ Datei '{filename}' ist leer.\n")
            return None
            
        header_info, characteristics, measurements = _parse_file_content(lines, logs)
        
        if not measurements:
            logs.append(f"⚠️ Keine gültigen Messwerte in '{filename}' gefunden.\n")
            return None
            
        logs.append(f"✅ Erfolgreich: {len(measurements)} Messwert-Datensätze gefunden.\n")
        return {'header_info': header_info, 'characteristics': characteristics, 'measurements': measurements}
    except Exception as e:
        logs.append(f"❌ Unerwarteter Fehler im Parser: {e}\n{traceback.format_exc()}\n")
        return None