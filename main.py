import serial
import cv2
from ultralytics import YOLO
import time

# 1. Ayarlar
MODEL_PATH = "models/best.pt" # Kendi dosya adını yaz
SERIAL_PORT = "/dev/ttyUSB0" # ESP32 portu
BAUD_RATE = 115200

# 2. Modelleri ve Portu Başlat
model = YOLO(MODEL_PATH) # YOLOv11 modelini yükle
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
cap = cv2.VideoCapture(0) # Jetson'a bağlı kamerayı aç

def main():
    print("Sistem Baslatiliyor...")
    while True:
        # --- A. GÖRÜNTÜ İŞLEME (AI) ---
        ret, frame = cap.read()
        if ret:
            results = model(frame, stream=True) # Kameradan gelen kareyi analiz et
            for r in results:
                # Burada bitki sağlığı veya hastalık tespiti sonuçlarını alabilirsin
                print(f"Tespit Edilen Nesne Sayısı: {len(r.boxes)}") 

        # --- B. SENSÖR VERİLERİ (ESP32) ---
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if "WT:" in line:
                print(f"Sensör Verisi: {line}") # WT:xx|AT:xx... formatı

        # Çıkış için 'q' tuşuna bas
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    ser.close()

if __name__ == "__main__":
    main()