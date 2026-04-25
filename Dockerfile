FROM python:3.10-slim

WORKDIR /app

# OpenCV ve sistem bağımlılıkları (Bunlar olmazsa YOLO çalışmaz)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Cache yapısını bozmamak için önce gereksinimler
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Tüm proje dosyalarını kopyala (YOLO modeli dahil)
COPY . .

# Konteynere 8000 portunu açmasını söyle
EXPOSE 8000

# Uygulamayı başlat
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
