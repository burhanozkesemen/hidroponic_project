#!/usr/bin/env python3
"""
ESP32 Serial Port Test & Debugging Tool
Tüm baud rate'leri dener, gelen verileri gösterir
"""

import serial
import time
import sys

def test_baud_rate(port='/dev/ttyUSB0', baud=115200, duration=3):
    """Belirtilen baud rate'te veri oku"""
    print(f"\n{'='*60}")
    print(f"🔍 Test: {port} @ {baud} baud (Timeout: {duration}s)")
    print('='*60)
    
    try:
        ser = serial.Serial(port, baud, timeout=0.5)
        time.sleep(0.2)  # Port açılması için bekle
        
        ser.reset_input_buffer()
        start_time = time.time()
        line_count = 0
        
        print(f"⏳ Veri bekleniyor...\n")
        
        while time.time() - start_time < duration:
            try:
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='replace').strip()
                    
                    if line:
                        line_count += 1
                        # Hex ve ASCII göster
                        print(f"[{line_count}] {line}")
                        
                        # Biçimi kontrol et
                        if "WT:" in line and "PH:" in line:
                            print(f"    ✅ GEÇERLI FORMAT BULUNDU! (WT: ve PH: var)")
                            ser.close()
                            return baud, True
                        elif ":" in line:
                            print(f"    ⚠️  Biçim tanınmadı ama ':' var")
            except Exception as e:
                print(f"    ⚠️  Decode hatası: {e}")
        
        ser.close()
        
        if line_count > 0:
            print(f"\n✅ Baud {baud} çalışıyor ({line_count} satır alındı)")
            return baud, True
        else:
            print(f"❌ Baud {baud} - veri yok")
            return baud, False
            
    except serial.SerialException as e:
        print(f"❌ Serial Hata: {e}")
        return baud, False
    except Exception as e:
        print(f"❌ Hata: {e}")
        return baud, False

def find_serial_ports():
    """USB portlarını bul"""
    import glob
    ports = []
    
    # Olası port kombinasyonları
    patterns = ['/dev/ttyUSB*', '/dev/ttyACM*', '/dev/tty.usbserial*', '/dev/tty.usbmodem*']
    
    for pattern in patterns:
        ports.extend(glob.glob(pattern))
    
    if ports:
        print(f"🔌 Bulundu: {ports}")
        return ports
    else:
        print("❌ Port bulunamadı!")
        return []

def main():
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "🌊 ESP32 SERIAL PORT TEST TOOL" + " "*13 + "║")
    print("╚" + "="*58 + "╝")
    
    # Port bul
    ports = find_serial_ports()
    if not ports:
        print("\n❌ USB port'u tarayamadı! Kontrol et:")
        print("   $ ls -la /dev/ttyUSB*")
        sys.exit(1)
    
    port = ports[0]
    
    # Tüm baud rate'leri test et
    baud_rates = [115200, 9600, 19200, 38400, 57600, 74880]  # 74880 = ESP32 default
    results = []
    
    for baud in baud_rates:
        detected_baud, has_data = test_baud_rate(port, baud, duration=2)
        if has_data:
            results.append((baud, True))
        else:
            results.append((baud, False))
    
    # Özet
    print(f"\n\n{'='*60}")
    print("📊 ÖZET:")
    print('='*60)
    
    working_bauds = [b for b, ok in results if ok]
    
    if working_bauds:
        print(f"✅ Çalışan baud rate'ler: {working_bauds}")
        print(f"\n🎯 ÖNERİ: server.py'de TEST_MODE = False yapıp")
        print(f"          detect_baud_rate() fonksiyonunu kontrol et")
    else:
        print("❌ Hiçbir baud rate'te veri alınamadı!")
        print("\n🔧 Kontrol Listesi:")
        print("   1. ESP32 'ye güç veriliyor mu?")
        print("   2. Arduino IDE Serial Monitor'da veri görülüyor mu?")
        print("   3. USB kablosu bağlı mı?")
        print("   4. Başka bir cihaz port'u kullanıyor mu?")
        print("\n5. Baud rate'i Arduino kodundan kontrol et:")
        print("   Serial.begin(115200)  ← bu değeri bize söyle")
    
    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    main()
