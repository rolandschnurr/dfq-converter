# parsers/messdate_parser.py

"""
Parser-Modul, das AUSSCHLIESSLICH für das Q-DAS MESSDATE-Format
mit mehreren Messungen pro Zeile zuständig ist.
"""
import re
import pandas as pd

def parse(line, characteristics, event_id, logs):
    """
    Versucht, eine Zeile als MESSDATE-Format zu parsen.
    """
    if 'e' in line.lower() and re.search(r'\d[Ee][+-]?\d', line):
        return None

    pattern = re.compile(
        r'([-+]?\d+\.?\d*)\s+(\d+)\s+(\d{1,2}\.\d{1,2}\.\d{4}/\d{1,2}:\d{1,2}:\d{1,2})'
    )
    matches = pattern.findall(line)
    if not matches:
        return None

    measurements = []
    for i, match_tuple in enumerate(matches):
        try:
            char_idx = i + 1
            value_str, attr_str, ts_str = match_tuple
            merkmal_info = characteristics.get(char_idx, {})
            merkmal_name = merkmal_info.get('K2002', merkmal_info.get('K2001', f'Merkmal_{char_idx}'))

            measurement = {
                'Event-ID': event_id,
                'Wert': float(value_str),
                'Attribut': int(attr_str),
                'Zeitstempel': pd.to_datetime(ts_str, format='%d.%m.%Y/%H:%M:%S', errors='coerce'),
                'Merkmal': merkmal_name
            }
            measurements.append(measurement)
        except (ValueError, IndexError):
            continue

    return measurements if measurements else None