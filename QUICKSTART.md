# Quick Start Guide - HydroAI

## 📋 Hangi Dosyayı Çalıştıracaksınız?

### **👉 `server.py` - Bu Dosyayı Çalıştırın!**

Proje için **web tabanlı dashboard** kullanıyorsanız, `server.py` dosyasını çalıştırmalısınız.

---

## 🚀 Kurulum & Çalıştırma Adımları

### 1️⃣ Gerekli Kütüphaneleri Kurun
```bash
pip install -r requirements.txt
```

### 2️⃣ Konfigürasyon Ayarlayın
`server.py` dosyasını açın ve şu satırları kontrol edin:

```python
SERIAL_PORT = "/dev/ttyUSB0"  # ESP32 USB portunuzu kontrol edin
BAUD_RATE = 115200            # (Varsayılan)
MODEL_PATH = "models/best.pt" # YOLO modelinin yolu
```

**ESP32 portunu bulma:**
```bash
# Linux/Mac
ls /dev/tty*

# Windows
# Device Manager'da COM portunu kontrol edin
```

### 3️⃣ Server'ı Başlatın
```bash
python server.py
```

**Çıktı şöyle görünecek:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 [press CTRL+C to quit]
```

### 4️⃣ Dashboard'a Erişin
Web tarayıcınızda şu adresi açın:
```
http://localhost:8000
```

---

## 📁 Dosya Yapısı & İşlevleri

| Dosya | İşlev |
|-------|-------|
| **server.py** | 🌐 Web Dashboard & API (Çalıştırın!) |
| **main.py** | 📺 Standalone script (Çevrimdışı kullanım) |
| **utils.py** | 🔧 Yardımcı fonksiyonlar |
| **models/best.pt** | 🤖 YOLO AI Modeli |
| **static/** | 🎨 HTML, CSS, JavaScript dosyaları |

---

## 💻 Sistem Gereksinimleri

✅ **Minimum:**
- Python 3.9+
- 2GB RAM
- USB kamerasıUSB ESP32

✅ **Önerilen (Daha İyi Performans):**
- NVIDIA GPU (CUDA)
- 8GB+ RAM
- High-speed USB 3.0

---

## 🔌 Hardware Bağlantıları

### ESP32 (Sensör Kartı)
```
USB A → USB Micro-B → ESP32
```
- **Seri Protokolü:** 115200 baud
- **Veri Formatı:** `WT:xx|AT:xx|H:xx|PH:xx|TDS:xx|WL:x`

### USB Kamera
```
USB A → USB Kamera
```
- **Default Device:** `/dev/video0`
- **Çözünürlük:** 1920x1080 önerilir

---

## 🌐 Dashboard Özellikleri

### 🏠 **Ana Sayfa (Dashboard)**
- Gerçek zamanlı sensör okumaları
- Canlı kamera yayını
- AI bitki tespiti

### 📊 **Analizler (Analytics)**
- Su parametreleri grafiği
- Bitki gelişim trendi
- Sistem verimliliği

### 📋 **Geçmiş Kayıtlar (History)**
- Tüm olayların kaydı
- CSV indirme seçeneği
- Tarih/saat ile filtreleme

### ⚙️ **Ayarlar (Settings)**
- Sensör limitlerini ayarlama
- pH, EC, sıcaklık thresholdları
- Otomasyon kuralları

---

## 🆘 Sorun Giderme

### ❌ **"Port açılamıyor" Hatası**
```bash
# Portu kullanan process'i bulun ve kapatın
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows
```

### ❌ **ESP32 Bağlantısı Kesildi**
```python
# server.py'de port değiştirin
# Doğru port için kontrol edin
python -m serial.tools.list_ports  # Tüm portları listele
```

### ❌ **Kamera Görüntüsü Gözükmüyor**
```bash
# Kamera cihazini kontrol edin
ls -la /dev/video*  # Hangi video device var?

# Kamera izinlerini kontrol edin
sudo usermod -a -G video $USER
```

### ❌ **GPU/CUDA Sorunu**
```bash
# GPU kullanılıp kullanılmadığını kontrol edin
python -c "import torch; print(torch.cuda.is_available())"

# CPU modunda çalıştırmak için server.py'de değiştirin:
# model = YOLO(MODEL_PATH, device='cpu')
```

---

## 📊 API Endpoints

```bash
# Sensör verisini al
curl http://localhost:8000/api/sensor-data

# Görüntü analiz et
curl -X POST -F "file=@image.jpg" http://localhost:8000/api/analyze-image

# Canlı video stream
curl http://localhost:8000/api/video_feed
```

---

## 🔐 Üretim Ortamı (Production)

Projeyi canlı ortamda çalıştırmak için:

1. ✅ Güvenlik ayarlarını aktif edin
2. ✅ CORS ayarlarını kısıtlayın
3. ✅ Veritabanı kullanın
4. ✅ HTTPS etkinleştirin
5. ✅ Yedekleme sistemi kurun

Detaylı bilgi için `README.md` dosyasına bakın.

---

## 📞 İletişim & Destek

Sorularınız için:
- 📧 Email: support@hydro.ai
- 🐛 Bug Rapor: GitHub Issues
- 💬 Sohbet: Discord Community

---

**Made with ❤️ for sustainable agriculture**

🌱 HydroAI v1.0.2
