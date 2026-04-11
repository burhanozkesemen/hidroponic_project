# HydroAI - Hydroponic Monitoring System

A sophisticated AI-powered hydroponic plant monitoring system with real-time sensor data collection, computer vision analysis, and interactive web dashboard.

![Version](https://img.shields.io/badge/version-1.0.2-blue)
![Status](https://img.shields.io/badge/status-Production-green)
![License](https://img.shields.io/badge/license-MIT-green)

## 🌱 Project Overview

HydroAI is an intelligent hydroponic cultivation system that combines:
- **YOLO-based Computer Vision**: Real-time plant detection and health analysis
- **IoT Sensor Integration**: ESP32-based environmental monitoring (pH, EC, Temperature, Humidity)
- **Real-time Dashboard**: Interactive web interface with live camera feed and sensor data
- **Data Analytics**: Historical trends and plant growth analysis

## ⚙️ System Architecture

```
┌─────────────────────────────────────────────────┐
│          HydroAI System Components               │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────┐         ┌─────────────────┐  │
│  │  ESP32 + USB │◄────────┤   Server.py     │  │
│  │  (Sensors)   │         │  (FastAPI)      │  │
│  └──────────────┘         └────────┬────────┘  │
│                                    │            │
│  ┌──────────────┐         ┌────────▼────────┐  │
│  │   Camera     │◄────────┤  AI Model       │  │
│  │  (YOLO)      │         │  (best.pt)      │  │
│  └──────────────┘         └────────┬────────┘  │
│                                    │            │
│                           ┌────────▼────────┐  │
│                           │   Web Dashboard │  │
│                           │   (Port 8000)   │  │
│                           └─────────────────┘  │
│                                                  │
└─────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- USB Serial connection to ESP32
- USB Camera
- NVIDIA GPU (recommended for YOLO inference)

### Installation

1. **Clone and Setup**
```bash
cd hidroponic_project
pip install -r requirements.txt
```

2. **Configure Hardware**
Edit `server.py` to set your configuration:
```python
SERIAL_PORT = "/dev/ttyUSB0"  # Change to your ESP32 port
BAUD_RATE = 115200
MODEL_PATH = "models/best.pt"
```

3. **Run the Application**
```bash
# Start the FastAPI server
python server.py

# The dashboard will be available at:
# http://localhost:8000
```

## 📊 Dashboard Features

### 🏠 Dashboard (Home)
- **Real-time Sensor Readings**
  - pH Level
  - Electrical Conductivity (EC)
  - Water Temperature
  - Ambient Humidity
  
- **Live Camera Feed**
  - Real-time plant detection
  - AI-powered plant health analysis
  - Detection statistics

- **System Status**
  - Server connectivity
  - Camera status
  - AI/Jetson status

### 📈 Analytics
- Historical sensor data visualization
- Trend analysis
- Growth pattern recognition

### 📋 History
- Complete sensor data logs
- Timestamped measurements
- Data export functionality

### ⚙️ Settings
- System configuration
- Sensor calibration
- Alert thresholds
- User preferences

## 🔧 Main Components

### `server.py`
FastAPI-based backend server handling:
- REST API endpoints
- Real-time video streaming
- Sensor data processing
- Image analysis with YOLO model
- Data persistence

**Key Endpoints:**
- `GET /` - Dashboard homepage
- `GET /api/sensor-data` - Current sensor readings
- `GET /api/video_feed` - Live camera stream
- `POST /api/analyze-image` - Analyze uploaded image
- `GET /analysis` - Analytics page
- `GET /history` - Historical data page
- `GET /settings` - Settings page

### `main.py`
Standalone script for offline operation:
- Direct camera and ESP32 communication
- YOLO model inference
- Data logging without web server

### `utils.py`
Utility functions:
- Data processing
- Calculations
- Helper methods

### AI Model
- **File**: `models/best.pt`
- **Framework**: YOLOv11 (Ultralytics)
- **Trained on**: Hydroponic plant detection
- **Accuracy**: Real-time detection at 30+ FPS

## 💻 Technologies Used

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI, Uvicorn |
| Frontend | HTML5, CSS3, JavaScript |
| AI/ML | YOLOv11, OpenCV |
| Hardware Interface | PySerial, OpenCV |
| Data Visualization | Chart.js |
| API Framework | FastAPI with CORS |

## 📋 Sensor Data Format

Data from ESP32 follows this format:
```
WT:25.4|AT:28.5|H:65|PH:6.8|TDS:1200|WL:1
```

| Key | Meaning | Unit |
|-----|---------|------|
| WT | Water Temperature | °C |
| AT | Air Temperature | °C |
| H | Humidity | % |
| PH | pH Level | pH |
| TDS | Total Dissolved Solids (EC) | ppm |
| WL | Water Level | 0=Full, 1=Low |

## 🎨 Web Interface

- **Modern Dark Theme**: Professional dark mode interface
- **Responsive Design**: Works on desktop and tablets
- **Real-time Updates**: WebSocket-based live data
- **Card-based Layout**: Clean, organized information display
- **Color Coding**: Visual indicators for system status

## 📝 Configuration

Edit `server.py` to customize:

```python
# Hardware Configuration
SERIAL_PORT = "/dev/ttyUSB0"      # ESP32 USB port
BAUD_RATE = 115200                # Serial baud rate
MODEL_PATH = "models/best.pt"     # YOLO model path

# Safety Thresholds
PH_MIN, PH_MAX = 5.5, 7.5
EC_MIN, EC_MAX = 800, 1400
TEMP_MIN, TEMP_MAX = 18, 30
```

## 🔴 Troubleshooting

### ESP32 Connection Issues
```bash
# Check available ports
ls /dev/tty* | grep USB

# Change port in server.py if needed
```

### Camera Not Showing
```bash
# Verify camera device
ls /dev/video*

# Update camera index in server.py (default: 0)
```

### YOLO Model Issues
```bash
# Ensure model file exists
ls -lh models/best.pt

# Check GPU availability
python -c "import torch; print(torch.cuda.is_available())"
```

## 📊 Performance Metrics

- **Inference Speed**: 30+ FPS on GPU
- **Sensor Data Rate**: 1 reading per second
- **Dashboard Response**: <100ms
- **Concurrent Users**: Up to 20

## 🔐 Security Notes

- CORS enabled for all origins (configure in production)
- No authentication layer (add for production deployment)
- Data stored locally (implement cloud backup)

## 📦 Deployment

### Docker Support (Optional)
```dockerfile
FROM python:3.9
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "server.py"]
```

### Production Checklist
- [ ] Disable CORS wildcards
- [ ] Add authentication/authorization
- [ ] Enable HTTPS/SSL
- [ ] Set up database for data persistence
- [ ] Configure automated backups
- [ ] Monitor API rate limits
- [ ] Add error logging/monitoring

## 📚 Endpoint Documentation

### Sensor Data
```bash
GET /api/sensor-data
```
Returns latest sensor readings

### Image Analysis
```bash
POST /api/analyze-image
Body: FormData with image file
```
Returns detection results and statistics

### Video Stream
```bash
GET /api/video_feed
```
Returns MJPEG stream

## 🤝 Contributing

1. Create feature branch
2. Make changes
3. Test thoroughly
4. Submit pull request

## 📄 License

MIT License - See LICENSE file for details

## 👨‍💻 Author

HydroAI Development Team

## 📞 Support

For issues and feature requests, please open an issue.

## 🔄 Version History

**v1.0.2** (Current)
- Production stable release
- Real-time sensor monitoring
- AI plant detection
- Web dashboard

**v1.0.1**
- Bug fixes and optimizations

**v1.0.0**
- Initial release

---

**Made with ❤️ for sustainable agriculture**
