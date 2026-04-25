# Python 3.10 tabanlı hafif imaj
FROM python:3.10-slim

# Çalışma dizini
WORKDIR /app

# OpenCV bağımlılıklarını kur (Yeni sürümlere uyumlu isimler)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Gereksinimleri kopyala ve kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Tüm dosyaları kopyala
COPY . .

# Konteynere 8000 portunu açmasını söyle
EXPOSE 8000

# Uygulamayı başlat
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]