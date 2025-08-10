#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test-Skript für BOSCH Q-DAS Datei Verarbeitung
Dieses Skript testet die Parsing-Funktionen ohne Flask
"""

import re
import pandas as pd
from datetime import datetime

def test_bosch_parsing():
    """Testet das Parsing der BOSCH-Datei"""
    
    # Beispiel-Messwertzeilen aus der BOSCH-Datei
    test_lines = [
        "6.00100000000000E+0000006.09.2002/12:41:27#0000",
        "6.00200000000000E+0000006.09.2002/12:41:29#0000",
        "5.99900000000000E+0000006.09.2002/12:43:21#0000"
    ]
    
    print("="*60)
    print("Test: BOSCH Q-DAS Format Parsing")
    print("="*60)
    
    measurements = []
    
    for line in test_lines:
        print(f"\nZeile: {line}")
        
        # Parse wissenschaftliche Notation
        sci_pattern = r'([-+]?\d*\.?\d+[Ee][+-]?\d+)'
        sci_match = re.search(sci_pattern, line)
        
        if sci_match:
            value_str = sci_match.group(1)
            value = float(value_str)
            print(f"  Wert (wiss. Notation): {value_str} = {value:.4f}")
            
            # Extrahiere Attribut
            attr_pattern = r'[Ee][+-]?\d+(\d{2})'
            attr_match = re.search(attr_pattern, line)
            attribute = int(attr_match.group(1)) if attr_match else 0
            print(f"  Attribut: {attribute}")
            
            # Extrahiere Datum/Zeit
            dt_pattern = r'(\d{2}\.\d{2}\.\d{4}/\d{2}:\d{2}:\d{2})'
            dt_match = re.search(dt_pattern, line)
            
            if dt_match:
                date_str = dt_match.group(1)
                timestamp = pd.to_datetime(date_str.replace('/', ' ', 1), 
                                         format='%d.%m.%Y %H:%M:%S')
                print(f"  Zeitstempel: {timestamp}")
            
            # Extrahiere Zusatzdaten
            if '#' in line:
                zusatz = line.split('#')[1] if len(line.split('#')) > 1 else ''
                print(f"  Zusatzdaten: {zusatz}")
            
            measurements.append({
                'Wert': value,
                'Attribut': attribute,
                'Zeitstempel': timestamp
            })
    
    # Statistik
    if measurements:
        df = pd.DataFrame(measurements)
        print("\n" + "="*60)
        print("Statistiken:")
        print("="*60)
        print(f"Anzahl Messungen: {len(df)}")
        print(f"Mittelwert: {df['Wert'].mean():.4f}")
        print(f"Min: {df['Wert'].min():.4f}")
        print(f"Max: {df['Wert'].max():.4f}")
        print(f"Std.Abw.: {df['Wert'].std():.4f}")
    
    # Test K-Feld Parsing
    print("\n" + "="*60)
    print("Test: K-Feld Parsing")
    print("="*60)
    
    k_fields = [
        "K0100 1",
        "K1001/1 0 433 171 914",
        "K1002/1 Hole type nozzle",
        "K2101/1 6.000",
        "K2110/1 5.97000",
        "K2111/1 6.03000"
    ]
    
    header_info = {}
    
    for line in k_fields:
        parts = line.split(' ', 1)
        if len(parts) >= 2:
            k_code = parts[0]
            value = parts[1] if len(parts) > 1 else ''
            header_info[k_code] = value
            print(f"{k_code}: {value}")
    
    # Zeige erkannte Toleranzen
    if 'K2110/1' in header_info and 'K2111/1' in header_info:
        usg = float(header_info['K2110/1'])
        osg = float(header_info['K2111/1'])
        print(f"\nToleranzbereich: {usg:.3f} - {osg:.3f} mm")
        print(f"Toleranz: {(osg-usg):.3f} mm")

def test_file_processing():
    """Testet die Verarbeitung einer kompletten BOSCH-Datei"""
    
    # Simuliere eine kleine BOSCH-Datei
    test_content = """K0100 1
K0101 2
K1001/1 0 433 171 914
K1002/1 Hole type nozzle
K1082/1 PAKO 9
K1204/1 04/16/2007
K2001/1 1
K2002/1 Corpus diameter
K2022/1 3
K2101/1 6.000
K2110/1 5.97000
K2111/1 6.03000
K2142/1 mm
K2202/1 1
K2213/1 6.002
K2220/1 1
K2221/1 1
K2222/1 50
6.00100000000000E+0000006.09.2002/12:41:27#0000
K0097/1 {7A4B6A52-31F9-4CA2-9067-10278D5098D0}
6.00200000000000E+0000006.09.2002/12:41:29#0000
K0097/1 {F5B489F2-123A-4A87-9653-6B86201849F4}
5.99900000000000E+0000006.09.2002/12:41:30#0000
K0097/1 {924BF010-05F3-4BAB-AAA5-002C50BAFF7A}"""

    lines = test_content.strip().split('\n')
    
    print("\n" + "="*60)
    print("Test: Komplette Dateiverarbeitung")
    print("="*60)
    
    header_info = {}
    characteristics = {}
    measurements = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        if line.startswith('K'):
            if re.match(r'^K\d{4}', line[:5]):
                # K-Feld
                parts = line.split(' ', 1)
                if len(parts) >= 2:
                    k_code = parts[0]
                    value = parts[1]
                    header_info[k_code] = value
                    
                    # Merkmalsdaten
                    if k_code.startswith('K2') and '/' in k_code:
                        base_code, idx = k_code.split('/', 1)
                        if idx == '1':
                            if 1 not in characteristics:
                                characteristics[1] = {}
                            characteristics[1][base_code] = value
            elif line.startswith('K0097'):
                # GUID für vorherigen Messwert
                if measurements:
                    parts = line.split(' ', 1)
                    if len(parts) > 1:
                        measurements[-1]['GUID'] = parts[1]
        else:
            # Messwertzeile
            sci_pattern = r'([-+]?\d*\.?\d+[Ee][+-]?\d+)'
            sci_match = re.search(sci_pattern, line)
            
            if sci_match:
                value = float(sci_match.group(1))
                
                # Datum/Zeit
                dt_pattern = r'(\d{2}\.\d{2}\.\d{4}/\d{2}:\d{2}:\d{2})'
                dt_match = re.search(dt_pattern, line)
                timestamp = None
                if dt_match:
                    date_str = dt_match.group(1)
                    timestamp = pd.to_datetime(date_str.replace('/', ' ', 1),
                                             format='%d.%m.%Y %H:%M:%S')
                
                measurements.append({
                    'Wert': value,
                    'Zeitstempel': timestamp,
                    'Merkmal': characteristics.get(1, {}).get('K2002', 'Messwert')
                })
    
    # Ausgabe
    print(f"\nHeader-Felder: {len(header_info)}")
    print(f"Merkmale: {len(characteristics)}")
    print(f"Messungen: {len(measurements)}")
    
    if measurements:
        df = pd.DataFrame(measurements)
        print("\nMesswerte:")
        print(df.to_string())
        
        print(f"\nReferenzwert: {header_info.get('K2213/1', 'N/A')}")
        print(f"Mittelwert: {df['Wert'].mean():.4f}")
        print(f"Abweichung: {df['Wert'].mean() - float(header_info.get('K2213/1', 0)):.4f}")

if __name__ == "__main__":
    print("Q-DAS BOSCH Format Test")
    print("="*60)
    
    # Test 1: Basis-Parsing
    test_bosch_parsing()
    
    # Test 2: Komplette Datei
    test_file_processing()
    
    print("\n" + "="*60)
    print("Tests abgeschlossen!")
    print("="*60)
