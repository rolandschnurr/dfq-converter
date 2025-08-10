#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test-Skript für MESSDATE.txt Format
Testet das komprimierte Multi-Merkmal Format
"""

import re
import pandas as pd

def test_messdate_format():
    """Testet das MESSDATE Format mit mehreren Merkmalen pro Zeile"""
    
    print("="*60)
    print("Test: MESSDATE Format (DC-BREMSSCHEIBE)")
    print("="*60)
    
    # Test-Header
    header_lines = [
        "K0100 6",
        "K1001 DREHEN OP30_2",
        "K1002 DC-BREMSSCHEIBE",
        "K2001/1 50.45",
        "K2022/1 6",
        "K2101/1 50.45",
        "K2110/1 50.30",
        "K2111/1 50.6",
        "K2142/1 MM",
        "K2001/2 L24.55",
        "K2022/2 6",
        "K2101/2 24.55",
        "K2110/2 24.4",
        "K2111/2 24.7",
        "K2142/2 MM",
        "K2001/3 D67 H9",
        "K2101/3 67.037",
        "K2110/3 67.000",
        "K2111/3 67.074",
        "K2001/4 L0",
        "K2101/4 0",
        "K2110/4 -.1",
        "K2111/4 0.1",
        "K2001/5 L7.5",
        "K2101/5 7.500",
        "K2110/5 7.400",
        "K2111/5 7.600"
    ]
    
    # Parse Header
    characteristics = {}
    header_info = {}
    
    for line in header_lines:
        parts = line.split(' ', 1)
        if len(parts) >= 2:
            k_code = parts[0]
            value = parts[1]
            header_info[k_code] = value
            
            if '/' in k_code:
                base_code, idx = k_code.split('/')
                if base_code.startswith('K2') and idx.isdigit():
                    idx = int(idx)
                    if idx not in characteristics:
                        characteristics[idx] = {}
                    characteristics[idx][base_code] = value
    
    print("\nErkannte Merkmale:")
    for idx, char in sorted(characteristics.items()):
        name = char.get('K2001', f'Merkmal {idx}')
        nenn = char.get('K2101', '')
        usg = char.get('K2110', '')
        osg = char.get('K2111', '')
        print(f"  {idx}. {name}: Nennmaß={nenn}, Toleranz=[{usg}, {osg}]")
    
    # Test Messwertzeilen
    test_lines = [
        "57.96205.7.2006/10:48:726.05105.7.2006/10:48:767.02905.7.2006/10:48:70.02105.7.2006/10:48:76.49905.7.2006/10:48:7",
        "57.96205.7.2006/10:48:826.05105.7.2006/10:48:867.02905.7.2006/10:48:80.02105.7.2006/10:48:86.49905.7.2006/10:48:8",
        "57.96205.7.2006/10:48:926.05105.7.2006/10:48:967.02905.7.2006/10:48:90.02105.7.2006/10:48:96.49905.7.2006/10:48:9"
    ]
    
    print("\n" + "="*60)
    print("Parsing Messwertzeilen:")
    print("="*60)
    
    all_measurements = []
    
    for line_num, line in enumerate(test_lines, 1):
        print(f"\nZeile {line_num}: {line[:50]}...")
        
        # Pattern für komprimiertes Format: Wert + Attribut + Datum
        # 57.962 0 5.7.2006/10:48:7
        pattern = r'(\d+\.?\d*)(0?)(\d{1,2}\.\d{1,2}\.\d{4}/\d{1,2}:\d{1,2}:\d{1,2})'
        matches = re.findall(pattern, line)
        
        print(f"  Gefundene Matches: {len(matches)}")
        
        for i, match in enumerate(matches):
            value_str, attr_str, date_str = match
            value = float(value_str)
            attribute = int(attr_str) if attr_str else 0
            
            # Parse Datum (5.7.2006/10:48:7 Format)
            # Normalisiere zu DD.MM.YYYY/HH:MM:SS
            date_parts = date_str.split('/')
            if len(date_parts) == 2:
                date_part, time_part = date_parts
                d, m, y = date_part.split('.')
                h, min, s = time_part.split(':')
                
                # Füge führende Nullen hinzu
                normalized = f"{d.zfill(2)}.{m.zfill(2)}.{y}/{h.zfill(2)}:{min.zfill(2)}:{s.zfill(2)}"
                
                try:
                    timestamp = pd.to_datetime(normalized.replace('/', ' '), 
                                             format='%d.%m.%Y %H:%M:%S')
                except:
                    timestamp = pd.Timestamp.now()
            
            # Merkmal zuordnen
            char_idx = i + 1
            merkmal_name = characteristics.get(char_idx, {}).get('K2001', f'Merkmal_{char_idx}')
            
            all_measurements.append({
                'Messung': line_num,
                'Merkmal': merkmal_name,
                'Wert': value,
                'Attribut': attribute,
                'Zeitstempel': timestamp
            })
            
            print(f"    Merkmal {char_idx} ({merkmal_name}): {value:.3f} (Attr={attribute})")
    
    # Erstelle DataFrame und zeige Statistiken
    if all_measurements:
        df = pd.DataFrame(all_measurements)
        
        print("\n" + "="*60)
        print("Zusammenfassung:")
        print("="*60)
        
        # Gruppiere nach Merkmal
        for merkmal in df['Merkmal'].unique():
            merkmal_df = df[df['Merkmal'] == merkmal]
            
            # Finde Toleranzen
            for idx, char in characteristics.items():
                if char.get('K2001') == merkmal:
                    usg = float(char.get('K2110', 0))
                    osg = float(char.get('K2111', 0))
                    nenn = float(char.get('K2101', 0))
                    break
            
            print(f"\n{merkmal}:")
            print(f"  Anzahl Messungen: {len(merkmal_df)}")
            print(f"  Mittelwert: {merkmal_df['Wert'].mean():.4f}")
            print(f"  Min: {merkmal_df['Wert'].min():.4f}")
            print(f"  Max: {merkmal_df['Wert'].max():.4f}")
            print(f"  Toleranz: [{usg:.3f}, {osg:.3f}]")
            
            # Prüfe ob innerhalb Toleranz
            in_tolerance = (merkmal_df['Wert'] >= usg) & (merkmal_df['Wert'] <= osg)
            print(f"  In Toleranz: {in_tolerance.sum()}/{len(merkmal_df)} ({100*in_tolerance.mean():.1f}%)")

def test_parsing_variants():
    """Testet verschiedene Parsing-Varianten"""
    
    print("\n" + "="*60)
    print("Test: Verschiedene Zeilenformate")
    print("="*60)
    
    test_cases = [
        # BOSCH Format
        ("6.00100000000000E+0000006.09.2002/12:41:27#0000", "BOSCH wissenschaftlich"),
        # MESSDATE komprimiert
        ("57.96205.7.2006/10:48:726.05105.7.2006/10:48:7", "MESSDATE komprimiert"),
        # Mit Leerzeichen
        ("57.962 0 5.7.2006/10:48:7 26.051 0 5.7.2006/10:48:7", "Mit Leerzeichen"),
        # Nur Werte
        ("50.450 24.550 67.029 0.021 7.499", "Nur Werte")
    ]
    
    for line, description in test_cases:
        print(f"\n{description}:")
        print(f"  Input: {line}")
        
        # Versuche verschiedene Pattern
        patterns = [
            (r'([-+]?\d*\.?\d+[Ee][+-]?\d+)', "Wissenschaftlich"),
            (r'(\d+\.?\d*)(0?)(\d{1,2}\.\d{1,2}\.\d{4}/\d{1,2}:\d{1,2}:\d{1,2})', "Komprimiert"),
            (r'(\d+\.?\d+)', "Dezimal")
        ]
        
        for pattern, name in patterns:
            matches = re.findall(pattern, line)
            if matches:
                print(f"    {name}: {len(matches)} Treffer")
                if len(matches) <= 5:
                    for match in matches[:5]:
                        print(f"      -> {match}")

if __name__ == "__main__":
    print("Q-DAS MESSDATE Format Test")
    print("="*60)
    
    # Test 1: MESSDATE Format
    test_messdate_format()
    
    # Test 2: Verschiedene Formate
    test_parsing_variants()
    
    print("\n" + "="*60)
    print("Tests abgeschlossen!")
    print("="*60)
    print("\nHinweis: Das erweiterte Programm unterstützt jetzt:")
    print("  ✓ BOSCH Format (wissenschaftliche Notation)")
    print("  ✓ MESSDATE Format (mehrere Merkmale pro Zeile)")
    print("  ✓ Verschiedene Datumsformate")
    print("  ✓ Komprimierte und expandierte Formate")