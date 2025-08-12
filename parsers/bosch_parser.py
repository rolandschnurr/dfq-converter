# parsers/bosch_parser.py

"""
Parser-Modul, das AUSSCHLIESSLICH für das Q-DAS Bosch-Format mit
wissenschaftlicher Notation zuständig ist.
"""
import pandas as pd

def parse(line, characteristics, event_id, logs):
    """
    Versucht, eine Zeile als Bosch-Format zu parsen.
    """
    if 'e' not in line.lower():
        return None

    try:
        parts = line.strip().split(maxsplit=2)
        if len(parts) < 3:
            return None

        value = float(parts[0])
        attribute = int(parts[1])
        ts_part = parts[2].split()[0]
        timestamp = pd.to_datetime(ts_part, format='%d.%m.%Y/%H:%M:%S', errors='coerce')

        if pd.isna(timestamp):
            return None

        merkmal_info = characteristics.get(1, {})
        merkmal_name = merkmal_info.get('K2002', "Unbekanntes Bosch-Merkmal")

        measurement = {
            'Event-ID': event_id,
            'Wert': value,
            'Attribut': attribute,
            'Zeitstempel': timestamp,
            'Merkmal': merkmal_name
        }
        return [measurement]
    except (ValueError, IndexError):
        return None