import uvicorn
from fastapi import FastAPI, Response, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
import cv2
import os, serial, threading, time, math, base64, numpy as np

app = FastAPI()

# --- 1. AYARLAR ---
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "best.pt")
STATIC_DIR = os.path.join(BASE_DIR, "static")

latest_sensor_data = {"ph": 0.0, "ec": 0.0, "temp": 0.0, "humidity": 0, "water_level": 100, "status": "Pasif"}
model = YOLO(MODEL_PATH)

# --- 2. YARDIMCI FONKSİYONLAR ---
def clean_val(val):
    """Bozuk verileri (nan, -127) temizler."""
    try:
        f = float(val)
        return 0.0 if math.isnan(f) or math.isinf(f) or f == -127.0 else f
    except: return 0.0

# --- 3. ESP32 VERİ OKUMA (Arka Plan) ---
def serial_worker():
    global latest_sensor_data
    while True:
        try:
            # Senin çalışan ayarın: /dev/ttyUSB0
            ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
            print("ESP32 Bağlantısı Başarılı ✅")
            while True:
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if "WT:" in line:
                        # Veri formatın: WT:xx|AT:xx|H:xx|PH:xx|TDS:xx|WL:x
                        d = dict(x.split(':') for x in line.split('|') if ':' in x)
                        latest_sensor_data = {
                            "ph": clean_val(d.get("PH", 0)),
                            "ec": clean_val(d.get("TDS", 0)),
                            "temp": clean_val(d.get("WT", 0)),
                            "humidity": int(clean_val(d.get("H", 0))),
                            "water_level": 100 if d.get("WL") == "0" else 10,
                            "status": "AKTİF"
                        }
                time.sleep(0.1)
        except Exception as e:
            latest_sensor_data["status"] = "BAĞLANTI YOK"
            time.sleep(5)

threading.Thread(target=serial_worker, daemon=True).start()

# --- 4. CANLI YOLO ANALİZİ VE YAYIN ---
def gen_frames():
    cap = cv2.VideoCapture(0) # Jetson kamerası
    while True:
        success, frame = cap.read()
        if not success: break
        
        # YOLOv11 ile her kareyi analiz et
        results = model(frame, stream=True, conf=0.4)
        for r in results:
            frame = r.plot() 
            
        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.get('/api/video_feed')
def video_feed():
    """index.html'deki img src buraya bağlanır."""
    return StreamingResponse(gen_frames(), media_type='multipart/x-mixed-replace; boundary=frame')

# --- 5. API VE STATİK DOSYA YÖNETİMİ ---
@app.get("/api/sensors")
async def get_sensors(): return latest_sensor_data

@app.post("/api/predict")
async def predict(file: UploadFile = File(...)):
    """Manuel resim yükleme analizi."""
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    res = model.predict(img, conf=0.25)[0]
    _, buffer = cv2.imencode('.jpg', res.plot())
    return {"image": f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"}

@app.get("/")
async def read_index(): return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/{page}")
async def read_other(page: str):
    path = os.path.join(STATIC_DIR, f"{page}.html")
    return FileResponse(path) if os.path.exists(path) else FileResponse(os.path.join(STATIC_DIR, "index.html"))

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)