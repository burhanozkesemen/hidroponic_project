# Python 3.10 tabanlı hafif imaj
FROM python:3.10-slim

# Çalışma dizini
WORKDIR /app

# Sistem bağımlılıkları (trixie sürümü için güncellenmiş paket isimleri)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Önce sadece gereksinimleri kopyala (Cache avantajı sağlar)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Projenin kalan tüm dosyalarını kopyala
COPY . .

# Uygulamayı 8000 portundan aç
EXPOSE 8000

# Başlatma komutu
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
