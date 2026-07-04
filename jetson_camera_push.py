"""Jetson Nano: kameralardan kare yakalayıp buluttaki /api/upload-frame'e gönderir.

Kullanım (Jetson'da, main.py ile birlikte ayrı bir terminalde):
    python3 jetson_camera_push.py

Ortam değişkenleriyle ayarlanabilir:
    CLOUD_URL=https://...azurewebsites.net  CAMERA_IDS=0,2  UPLOAD_INTERVAL=10
"""
import logging
import os
import time

import cv2
import requests

CLOUD_URL = os.getenv(
    "CLOUD_URL",
    "https://hydroponicsystem-fmg7gmhpgegfgvfc.italynorth-01.azurewebsites.net",
).rstrip("/")
CAMERA_IDS = [int(x) for x in os.getenv("CAMERA_IDS", "0,2").split(",")]
UPLOAD_INTERVAL = float(os.getenv("UPLOAD_INTERVAL", "10"))  # saniye
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", "70"))
FRAME_WIDTH = int(os.getenv("FRAME_WIDTH", "640"))
FRAME_HEIGHT = int(os.getenv("FRAME_HEIGHT", "480"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("camera_push")


def capture_frame(camera_id: int):
    """Kamerayı aç, tek kare al, kapat. (Sürekli açık tutmak USB kameralarda sorun çıkarabiliyor.)"""
    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    # Tamponu boşalt, güncel kareyi al
    for _ in range(3):
        cap.grab()
    ok, frame = cap.read()
    cap.release()
    if not ok:
        return None
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    return buf.tobytes() if ok else None


def upload(camera_id: int, jpeg: bytes) -> bool:
    try:
        r = requests.post(
            f"{CLOUD_URL}/api/upload-frame/{camera_id}",
            data=jpeg,
            headers={"Content-Type": "image/jpeg"},
            timeout=15,
        )
        return r.status_code == 200
    except requests.RequestException as exc:
        logger.warning("Yükleme hatası (cam %s): %s", camera_id, exc)
        return False


def main():
    logger.info("Kamera aktarımı başladı: %s -> %s (her %ss)", CAMERA_IDS, CLOUD_URL, UPLOAD_INTERVAL)
    while True:
        start = time.time()
        for cam_id in CAMERA_IDS:
            jpeg = capture_frame(cam_id)
            if jpeg is None:
                logger.warning("Kamera %s'den kare alınamadı", cam_id)
                continue
            if upload(cam_id, jpeg):
                logger.info("Cam %s: %d KB gönderildi", cam_id, len(jpeg) // 1024)
        # Aralığı koru
        elapsed = time.time() - start
        time.sleep(max(1.0, UPLOAD_INTERVAL - elapsed))


if __name__ == "__main__":
    main()
