import uvicorn
from fastapi import FastAPI, Response, UploadFile, File, Request, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from ultralytics import YOLO
import cv2
import os, serial, threading, time, math, base64, numpy as np
from datetime import datetime

# --- 1. ORTAM KONTROLÜ VE LİFESPAN (YENİ NESİL BAŞLATMA) ---
# Azure Portal'da 'AZURE_CLOUD' değişkenini 'true' yaparsan bulut modu aktif olur.
IS_CLOUD = os.getenv("AZURE_CLOUD", "false").lower() == "true"
PORT = int(os.getenv("PORT", 8000))

def start_background_tasks():
    # Sadece bulutta DEĞİLSEK seri portu dinlemeye başla
    if not IS_CLOUD:
        threading.Thread(target=serial_worker, daemon=True).start()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Uygulama başlarken çalışacak kodlar (Eski on_event yerine)
    print("✅ Sistem başlatılıyor...")
    start_background_tasks()
    yield
    # Uygulama kapanırken çalışacak kodlar
    print("❌ Sistem kapatılıyor...")

# Uygulamayı yeni lifespan yapısıyla ayağa kaldır
app = FastAPI(lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "best.pt")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# TEST_MODE: Bulutta donanım olmadığı için otomatik açılır
TEST_MODE = IS_CLOUD 

latest_sensor_data = {
    "ph": 0.0,
    "ec": 0.0,
    "temp": 0.0,
    "humidity": 0,
    "water_level": 0,
    "status": "BULUT MODU" if IS_CLOUD else "BAŞLATILIYOR"
}

model = None
model_loaded = False

def get_model():
    global model, model_loaded
    if not model_loaded and os.path.exists(MODEL_PATH):
        try:
            print("🤖 YOLO modeli yükleniyor...")
            model = YOLO(MODEL_PATH)
            model_loaded = True
            print("✅ YOLO modeli yüklendi")
        except Exception as e:
            print(f"⚠️ YOLO yükleme hatası: {e}")
            model_loaded = True
    return model

# --- 2. YARDIMCI FONKSİYONLAR ---
def clean_val(val):
    try:
        f = float(val)
        return 0.0 if math.isnan(f) or math.isinf(f) or f == -127.0 else f
    except: return 0.0

# --- 3. SERİAL WORKER (SADECE YERELDE ÇALIŞIR) ---
def serial_worker():
    global latest_sensor_data
    if IS_CLOUD: return # Bulutta seri port arama

    ser = None
    while True:
        try:
            if ser is None or not ser.is_open:
                # Jetson Nano'da ESP32 genelde ttyUSB0'dadır
                ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=2)
                print("✅ ESP32 Bağlandı!")
            
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if "WT:" in line and "PH:" in line:
                    parts = line.split('|')
                    d = {p.split(':')[0]: p.split(':')[1] for p in parts if ':' in p}
                    
                    latest_sensor_data = {
                        "ph": clean_val(d.get("PH", 0)),
                        "ec": clean_val(d.get("TDS", 0)),
                        "temp": clean_val(d.get("WT", 25.0)),
                        "humidity": int(clean_val(d.get("H", 0))),
                        "water_level": int(clean_val(d.get("WL", 0))),
                        "status": "AKTİF"
                    }
        except Exception as e:
            ser = None
            time.sleep(2)

# --- 4. API ENDPOINTLERİ ---

@app.get("/api/sensors")
async def get_sensors():
    return latest_sensor_data

@app.post("/api/update-sensors")
async def update_sensors(data: dict):
    """Jetson Nano'dan gelen veriyi Azure'da günceller"""
    global latest_sensor_data
    if IS_CLOUD:
        latest_sensor_data.update(data)
        latest_sensor_data["status"] = "JETSON'DAN GELDİ"
        return {"status": "success"}
    return {"status": "ignored_local"}

# 404 HATASINI ÇÖZEN KISIM: Arayüzden gelen frame/0 veya frame/2 isteklerini yakalar
@app.get('/api/frame/{camera_id}')
def get_frame(camera_id: int):
    return StreamingResponse(gen_frames(camera_id=camera_id), media_type='multipart/x-mixed-replace; boundary=frame')

@app.get('/api/video_feed')
def video_feed():
    # Geriye dönük uyumluluk için
    return StreamingResponse(gen_frames(camera_id=0), media_type='multipart/x-mixed-replace; boundary=frame')

# --- 5. KAMERA VE YOLO ---
def gen_frames(camera_id=0):
    if IS_CLOUD:
        # Bulutta kamera yok, sabit bir "Cloud Mode" karesi döndür
        while True:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, f"CLOUD MODE - CAM {camera_id}", (100, 200), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(frame, "Waiting for Jetson Nano...", (100, 240), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            ret, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(1)
    else:
        # Yerelde (Jetson) gerçek kamera akışı
        cap = cv2.VideoCapture(camera_id)
        
        # Kamera bağlanamazsa sistemin çökmesini engelle
        if not cap.isOpened():
            while True:
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(frame, f"CAM {camera_id} ERROR", (150, 240), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                ret, buffer = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                time.sleep(1)

        while True:
            success, frame = cap.read()
            if not success: break
            
            current_model = get_model()
            if current_model:
                results = current_model(frame, stream=True, conf=0.4)
                for r in results: frame = r.plot()
                
            ret, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# --- 6. BAŞLANGIÇ ---
@app.get("/")
async def read_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=PORT, reload=False)