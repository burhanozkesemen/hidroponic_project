import uvicorn
from fastapi import FastAPI, Response, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
import cv2
import os, serial, threading, time, math, base64, numpy as np
from datetime import datetime

app = FastAPI()

# --- 1. AYARLAR ---
# Cache busting için timestamp
CACHE_BUSTER = int(datetime.now().timestamp())

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Cache kontrol middleware
@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.endswith(".html"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "best.pt")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# TEST MODE (ESP32 & Kamera olmadan test etmek için)
TEST_MODE = False  # True = Hızlı, False = Gerçek cihazlar

latest_sensor_data = {
    "ph": 6.8,
    "ec": 1.2,
    "temp": 24.5,
    "humidity": 65,
    "water_level": 85,
    "status": "AKTİF"
}
# DEBUG: ESP32'den gelen raw veriyi tutmak için
debug_buffer = {
    "last_raw_line": "No data received yet",
    "raw_dict": {},
    "parse_errors": []
}
# YOLO modelini lazy loading ile yükle (hızlandır)
model = None
model_loaded = False

def get_model():
    global model, model_loaded
    if not model_loaded and not TEST_MODE and os.path.exists(MODEL_PATH):
        try:
            print("🤖 YOLO modeli yükleniyor...")
            model = YOLO(MODEL_PATH)
            model_loaded = True
            print("✅ YOLO modeli yüklendi")
        except Exception as e:
            print(f"⚠️  YOLO model yükleme hatası: {e}")
            model_loaded = True
    return model

# --- 2. YARDIMCI FONKSİYONLAR ---
def clean_val(val):
    """Bozuk verileri (nan, -127) temizler."""
    try:
        f = float(val)
        return 0.0 if math.isnan(f) or math.isinf(f) or f == -127.0 else f
    except: return 0.0

# --- 3. BAUD RATE AUTO DETECT ---
def detect_baud_rate():
    """Doğru baud rate'i bulur (en hızlı ilk bulduğu)."""
    baud_rates = [115200, 9600, 19200, 38400, 57600]  # 115200 ilk
    
    for baud in baud_rates:
        try:
            print(f"🔍 Baud {baud} deniyorum...")
            ser = serial.Serial('/dev/ttyUSB0', baud, timeout=0.2)
            time.sleep(0.1)
            
            # 3 satır oku, bir tanesi düzgün mi diye kontrol et
            valid_lines = 0
            start = time.time()
            while time.time() - start < 3 and valid_lines < 1:
                try:
                    if ser.in_waiting > 0:
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        if line and len(line) > 5:  # Boş değilse
                            if ":" in line:  # Biçim kontrol
                                valid_lines += 1
                                print(f"✅ {baud} baud'da veri bulundu: {line[:30]}...")
                                ser.close()
                                return baud
                except:
                    pass
                    
            ser.close()
        except Exception as e:
            pass
    
    print(f"⚠️  Baud rate bulunamadı, {115200} kullanılacak...")
    return 115200

# --- 4. ESP32 VERİ OKUMA (Arka Plan) ---
def serial_worker():
    global latest_sensor_data, debug_buffer
    if TEST_MODE:
        # Test modunda dummy veri gönder
        import random
        while True:
            latest_sensor_data = {
                "ph": round(6.5 + random.uniform(-0.3, 0.3), 2),
                "ec": round(1.2 + random.uniform(-0.1, 0.2), 2),
                "temp": round(24 + random.uniform(-1, 1), 1),
                "humidity": 60 + random.randint(-5, 5),
                "water_level": 85 + random.randint(-10, 10),
                "status": "AKTİF"
            }
            time.sleep(2)
        return
    
    ser = None
    reconnect_count = 0
    baud_rate = 115200
    
    while True:
        try:
            # Bağlantı yoksa aç
            if ser is None or not ser.is_open:
                # İlk bağlantıysa baud rate'i bul
                if reconnect_count == 0:
                    baud_rate = detect_baud_rate()
                
                ser = serial.Serial('/dev/ttyUSB0', baud_rate, timeout=2)
                ser.reset_input_buffer()
                reconnect_count = 0
                print(f"✅ ESP32 Bağlandı! (Baud: {baud_rate}) [{datetime.now().strftime('%H:%M:%S')}]")
                latest_sensor_data["status"] = "BAĞLANDI"
            
            # Veri oku
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                
                if not line:
                    time.sleep(0.05)
                    continue
                
                # DEBUG: Raw veriyi kaydet
                debug_buffer["last_raw_line"] = line
                debug_buffer["timestamp"] = datetime.now().isoformat()
                
                # Geçerli ESP32 veri satırı mı kontrol et
                if "WT:" in line and "PH:" in line:
                    try:
                        # Veri parse et
                        parts = line.split('|')
                        d = {}
                        for part in parts:
                            if ':' in part:
                                key, val = part.split(':', 1)
                                d[key.strip()] = val.strip()
                        
                        debug_buffer["raw_dict"] = d
                        debug_buffer["parse_errors"] = []
                        
                        # Verileri işle
                        ph_val = clean_val(d.get("PH", 0))
                        ec_val = clean_val(d.get("TDS", 0))
                        temp_val = clean_val(d.get("WT", 0))
                        humidity_val = int(clean_val(d.get("H", 0)))
                        wl_val = int(clean_val(d.get("WL", 85)))
                        
                        # EC/TDS sensörü değişken değerler gönderebilir (0-2000)
                        # Temp sensörü bağlı değilse 0.0 gelebilir - default 25°C ver
                        if temp_val == 0.0:
                            temp_val = 25.0  # Default ortam sıcaklığı
                        
                        # Verileri validasyon ile kaydet (EC: 0-2000 ppm/mS/cm)
                        if 0 <= ph_val <= 14 and 0 <= ec_val <= 2000 and -20 <= temp_val <= 60:
                            latest_sensor_data = {
                                "ph": ph_val,
                                "ec": ec_val,
                                "temp": temp_val,
                                "humidity": humidity_val,
                                "water_level": wl_val,
                                "status": "AKTİF"
                            }
                            print(f"📊 [{datetime.now().strftime('%H:%M:%S')}] pH={ph_val}, EC={ec_val:.0f}, T={temp_val:.1f}°C, H={humidity_val}%, WL={wl_val}%")
                        else:
                            error_msg = f"Veri aralığı hatası: pH={ph_val}, EC={ec_val}, T={temp_val}"
                            debug_buffer["parse_errors"].append(error_msg)
                            print(f"⚠️  {error_msg}")
                        
                    except Exception as parse_error:
                        error_msg = f"Parse hatası: {str(parse_error)}"
                        debug_buffer["parse_errors"].append(error_msg)
                        print(f"⚠️  {error_msg} | Raw: {line}")
                else:
                    # Geçersiz format, debug buffer'a kaydet
                    if line and len(line) < 100:  # Çok kısa değilse
                        print(f"🔍 Beklenen format bulunamadı: {line[:50]}...")
            else:
                time.sleep(0.05)  # CPU kullanımını azalt
                
        except serial.SerialException as e:
            ser = None
            reconnect_count += 1
            latest_sensor_data["status"] = f"BAĞLANTI YOK ({e.errno})"
            print(f"❌ Serial hatası: {e} | Yeniden deneme {reconnect_count}...")
            time.sleep(2)
        except Exception as e:
            ser = None
            latest_sensor_data["status"] = "HATA"
            print(f"❌ Beklenmeyen hata: {e}")
            time.sleep(2)

@app.on_event("startup")
async def startup_event():
    print("\n" + "="*60)
    print("🚀 HydroAI Server Başlıyor...")
    print(f"📍 TEST_MODE: {TEST_MODE}")
    print(f"🤖 Model Path: {MODEL_PATH}")
    print(f"📁 Static Dir: {STATIC_DIR}")
    print("="*60 + "\n")
    
    # Serial worker thread'i başlat
    threading.Thread(target=serial_worker, daemon=True).start()
    print("✅ Serial worker thread başlatıldı")

# --- 4. CANLI YOLO ANALİZİ VE YAYIN ---
def gen_frames(camera_id=0):
    """Kamera feed'i işle (0 = /dev/video0, 2 = /dev/video2) - Otomatik reconnect ile"""
    if TEST_MODE:
        # Test modunda hızlı test kare gönder
        counter = 0
        while True:
            counter += 1
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame[:, :] = [10, 30, 40]  # Koyu arka plan
            
            cam_label = "Camera 1 (/dev/video0)" if camera_id == 0 else "Camera 2 (/dev/video2)"
            cv2.putText(frame, "TEST MODE - Demo Stream", (120, 150), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, (16, 185, 129), 2)
            cv2.putText(frame, f"Frame: {counter}", (250, 200), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (148, 163, 184), 1)
            cv2.putText(frame, cam_label, (140, 260), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (94, 163, 184), 1)
            
            ret, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.05)  # ~20 FPS
    else:
        reconnect_attempts = 0
        max_reconnect_attempts = 5
        
        # İlk başta "Initializing..." kare gönder
        for _ in range(10):  # 0.5 saniye boyunca loading göster
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame[:, :] = [15, 25, 35]
            cam_label = "Camera 1 (/dev/video0)" if camera_id == 0 else "Camera 2 (/dev/video2)"
            cv2.putText(frame, f"Initializing {cam_label}...", (70, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.9, (16, 185, 129), 2)
            ret, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.05)
        
        while reconnect_attempts < max_reconnect_attempts:
            try:
                cap = cv2.VideoCapture(camera_id)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer for low latency
                cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)   # Disable autofocus for speed
                
                if not cap.isOpened():
                    reconnect_attempts += 1
                    print(f"⚠️  Kamera {camera_id} açılmadı (Deneme {reconnect_attempts}/{max_reconnect_attempts})")
                    
                    # Retry mesajı frame'i gönder
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    frame[:, :] = [20, 20, 40]
                    cv2.putText(frame, f"Camera Retry ({reconnect_attempts}/5)...", (110, 240),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 200), 2)
                    ret, buffer = cv2.imencode('.jpg', frame)
                    for _ in range(10):
                        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                        time.sleep(0.1)
                    continue
                
                # Kamera çözünürlüğünü ayarla
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_FPS, 20)
                reconnect_attempts = 0  # Reset on success
                print(f"✅ Kamera {camera_id} bağlandı")
                
                error_count = 0
                max_errors = 15
                frame_count = 0
                
                while error_count < max_errors:
                    try:
                        success, frame = cap.read()
                        
                        if not success:
                            error_count += 1
                            print(f"⚠️  Kamera {camera_id} frame okunamadı ({error_count}/{max_errors})")
                            
                            if error_count >= max_errors:
                                print(f"❌ Kamera {camera_id} çok hata verdi, yeniden bağlanıyor...")
                                break
                            
                            # Hata kare göster (mavi loading frame)
                            frame = np.zeros((480, 640, 3), dtype=np.uint8)
                            frame[:, :] = [20, 20, 50]
                            cv2.putText(frame, f"Camera {camera_id}: Waiting...", (140, 240),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 150, 255), 2)
                            ret, buffer = cv2.imencode('.jpg', frame)
                            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                            time.sleep(0.1)
                            continue
                        
                        # Frame başarılı, error count sıfırla
                        error_count = 0
                        frame_count += 1
                        
                        # YOLOv11 ile analiz (sadece model yüklüyse)
                        current_model = get_model()
                        if current_model and frame_count % 1 == 0:  # Her frame'i analiz et
                            try:
                                results = current_model(frame, stream=True, conf=0.4)
                                for r in results:
                                    frame = r.plot()
                            except Exception as e:
                                print(f"⚠️  Model analiz hatası Camera {camera_id}: {e}")
                        
                        ret, buffer = cv2.imencode('.jpg', frame)
                        if ret:
                            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                        
                        time.sleep(0.048)  # ~20 FPS
                        
                    except Exception as e:
                        error_count += 1
                        print(f"❌ Kamera {camera_id} frame hatası: {e}")
                        time.sleep(0.1)
                
                cap.release()
                print(f"⚠️  Kamera {camera_id} kesildi, reconnect deneniyor...")
                reconnect_attempts += 1
                time.sleep(0.5)  # Reconnect öncesi kısa bekle
                
            except Exception as e:
                reconnect_attempts += 1
                print(f"❌ Kamera {camera_id} genel hatası: {e}")
                time.sleep(0.5)
        
        # Max reconnect attempts exceeded
        print(f"❌ Kamera {camera_id} bağlanamadı ({max_reconnect_attempts} deneme sonrası)")
        while True:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame[:, :] = [30, 10, 10]
            cv2.putText(frame, f"Camera {camera_id}: OFFLINE", (130, 220),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 255), 2)
            cv2.putText(frame, "Check /dev/video0 or /dev/video2", (80, 280),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 200), 1)
            ret, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(1)

@app.get('/api/video_feed')
def video_feed():
    """Kamera 1 (/dev/video0)"""
    return StreamingResponse(gen_frames(camera_id=0), media_type='multipart/x-mixed-replace; boundary=frame')

@app.get('/api/video_feed_2')
def video_feed_2():
    """Kamera 2 (/dev/video2)"""
    return StreamingResponse(gen_frames(camera_id=2), media_type='multipart/x-mixed-replace; boundary=frame')

# Cache en son frame'i (herbir kamera için)
last_frames = {0: None, 2: None}

def get_camera_frame(camera_id=0):
    """Kamera'dan tek frame al (JPEG binary)"""
    global frame_count
    
    if TEST_MODE:
        # Test frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :] = [10, 30, 40]
        cv2.putText(frame, "TEST MODE", (150, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (16, 185, 129), 2)
        ret, buffer = cv2.imencode('.jpg', frame)
        return buffer.tobytes() if ret else None
    
    try:
        cap = cv2.VideoCapture(camera_id)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 20)
        
        if not cap.isOpened():
            return None
        
        success, frame = cap.read()
        cap.release()
        
        if not success or frame is None:
            return None
        
        frame_count += 1
        
        # YOLOv11 process (every frame)
        current_model = get_model()
        if current_model:
            try:
                results = current_model(frame, stream=True, conf=0.4)
                for r in results:
                    frame = r.plot()
            except Exception as e:
                print(f"Model error: {e}")
        
        ret, buffer = cv2.imencode('.jpg', frame)
        return buffer.tobytes() if ret else None
        
    except Exception as e:
        print(f"Camera {camera_id} error: {e}")
        return None

frame_count = 0

def cache_frames():
    """Background thread: continuously cache latest frames"""
    global frame_count
    while True:
        try:
            for cam_id in [0, 2]:
                jpeg = get_camera_frame(cam_id)
                if jpeg:
                    last_frames[cam_id] = jpeg
                    frame_count += 1
            time.sleep(0.1)  # 10 Hz polling
        except Exception as e:
            print(f"Cache thread error: {e}")
            time.sleep(1)

# Start frame cache thread
threading.Thread(target=cache_frames, daemon=True).start()

@app.get('/api/frame/{camera_id}')
async def get_frame(camera_id: int = 0):
    """Get latest cached frame"""
    if camera_id in last_frames and last_frames[camera_id]:
        return Response(content=last_frames[camera_id], media_type="image/jpeg")
    
    return {"error": f"Camera {camera_id} no frame"}

# --- 5. API VE STATİK DOSYA YÖNETİMİ ---
@app.get("/api/sensors")
@app.get("/api/sensor-data")
async def get_sensors():
    """Sensör verilerini döndür"""
    return {
        **latest_sensor_data,
        "pump_status": "active" if latest_sensor_data["status"] == "AKTİF" else "inactive"
    }

@app.post("/api/predict")
@app.post("/api/analyze-image")
async def predict(file: UploadFile = File(...)):
    """Manuel resim yükleme analizi."""
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return {"error": "Image decode failed", "counts": {}, "total": 0}
        
        # YOLO ile analiz
        current_model = get_model()
        if current_model and not TEST_MODE:
            try:
                results = current_model.predict(img, conf=0.25)
                res = results[0]
                
                # Tespit edilen nesneleri say
                detection_counts = {}
                for box in res.boxes:
                    class_id = int(box.cls[0])
                    class_name = res.names[class_id]
                    detection_counts[class_name] = detection_counts.get(class_name, 0) + 1
                
                annotated_frame = res.plot()
            except Exception as e:
                print(f"❌ Model tahmin hatası: {e}")
                annotated_frame = img
                detection_counts = {}
        else:
            # Test modunda örnek veri döndür
            annotated_frame = img
            detection_counts = {"Healthy Plant": 3, "Diseased Plant": 1} if TEST_MODE else {}
        
        _, buffer = cv2.imencode('.jpg', annotated_frame)
        
        return {
            "image": f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}",
            "counts": detection_counts,
            "total": sum(detection_counts.values()) if detection_counts else 0
        }
    except Exception as e:
        print(f"❌ Predict endpoint hatası: {e}")
        return {"error": str(e), "counts": {}, "total": 0}

@app.get("/api/debug")
async def debug_info():
    """🔍 ESP32 veri debug bilgisi"""
    return {
        "test_mode": TEST_MODE,
        "last_raw_data": debug_buffer["last_raw_line"],
        "parsed_dict": debug_buffer["raw_dict"],
        "current_sensor_data": latest_sensor_data,
        "parse_errors": debug_buffer["parse_errors"],
        "message": "ESP32'den gelen raw veriyi kontrol etmek için bu endpoint'i kullan"
    }

@app.get("/api/sensor-history")
async def get_sensor_history():
    """Sensör geçmişi (simüle)"""
    return {
        "labels": ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"],
        "ph": [6.0, 5.9, 5.8, 6.1, 6.2, 6.0],
        "ec": [1.2, 1.3, 1.2, 1.4, 1.5, 1.4],
        "temp": [24, 24.5, 25, 26, 25.5, 24]
    }

@app.get("/api/events")
async def get_events():
    """Sistem olayları ve alarm geçmişi"""
    return {
        "events": [
            {"timestamp": "2026-02-12 14:30", "type": "Image Analysis", "detail": "Plant count completed", "status": "success"},
            {"timestamp": "2026-02-12 12:15", "type": "Sensor Alert", "detail": "pH value low", "status": "warning"},
            {"timestamp": "2026-02-12 09:00", "type": "Automation", "detail": "LED lights activated", "status": "success"}
        ]
    }

@app.get("/")
async def read_index(): 
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/{page}")
async def read_other(page: str):
    path = os.path.join(STATIC_DIR, f"{page}.html")
    if os.path.exists(path):
        return FileResponse(path)
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)