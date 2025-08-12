# k_fields_loader.py

"""
Modul zum Laden und Parsen der K-Feld-Definitionen aus einer externen Datei.
"""

def load_k_field_map(filepath):
    """
    Lädt die K-Feld-Definitionen aus einer externen Textdatei im Format 'KEY = WERT'.

    Args:
        filepath (str): Der Pfad zur Definitionsdatei (z.B. "k_fields.txt").

    Returns:
        dict: Ein Wörterbuch, das K-Feld-Schlüssel auf ihre Beschreibungen abbildet.
    """
    k_map = {}
    print(f"[INFO] Lade K-Feld Definitionen aus '{filepath}'...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    k_map[key.strip()] = value.strip()
    except FileNotFoundError:
        print(f"[WARNUNG] Definitionsdatei '{filepath}' nicht gefunden. K-Feld-Bezeichnungen werden fehlen.")
    
    print(f"[INFO] {len(k_map)} K-Feld Definitionen erfolgreich geladen.")
    return k_map