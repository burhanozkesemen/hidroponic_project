#!/usr/bin/env python3
"""
ESP32 Baud Rate Finder - Tüm hızları sistem
"""

import serial
import time

def quick_test(port='/dev/ttyUSB0', baud=115200):
    """Hızlı test - ilk 5 satırı al"""
    try:
        ser = serial.Serial(port, baud, timeout=0.2)
        time.sleep(0.5)
        ser.reset_input_buffer()
        
        lines = []
        start = time.time()
        while time.time() - start < 1.5 and len(lines) < 5:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='replace').strip()
                if line:
                    lines.append(line)
        
        ser.close()
        return lines
        
    except:
        return []

print("\n🔍 ESP32 Baud Rate Finder\n")
print("="*60)

# En muhtemel baud rate'ler
bauds = [9600, 19200, 38400, 57600, 74880, 115200]

results = {}
for baud in bauds:
    lines = quick_test(baud=baud)
    if lines:
        results[baud] = lines
        status = "✅"
        if "WT:" in lines[0]:
            status += " VALID"
        print(f"{status} {baud:6d}: {lines[0][:40]}...")
    else:
        print(f"❌ {baud:6d}: -")

print("="*60)

# Sonuç
if results:
    print("\n✅ Veri alındı!")
    for baud, lines in results.items():
        if "WT:" in lines[0]:
            print(f"\n🎯 KULLAN: {baud}")
            print(f"   server.py'de 115200 yerine {baud} yazacağız")
            break
else:
    print("\n❌ Hiç veri alınamadı!")
    print("\nKontrol et:")
    print("1. Arduino IDE Serial Monitor'da görülüyor mu?")
    print("2. Baud rate kaç? (Serial.begin(?) değeri)")
    print("3. USB kablosu USB3 ise USB2'ye tak")

print()
