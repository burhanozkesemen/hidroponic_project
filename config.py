import os


class AppConfig:
    """Configuration loaded from environment variables or default values."""

    ENDPOINT_URL = os.getenv(
        "ENDPOINT_URL",
        "https://hydroponicsystem-fmg7gmhpgegfgvfc.italynorth-01.azurewebsites.net/ingest",
    )
    SERIAL_PORT = os.getenv("SERIAL_PORT", "/dev/ttyUSB0")
    BAUD_RATE = int(os.getenv("BAUD_RATE", "115200"))
    SERIAL_TIMEOUT = float(os.getenv("SERIAL_TIMEOUT", "1.0"))
    SERIAL_RECONNECT_INTERVAL = float(os.getenv("SERIAL_RECONNECT_INTERVAL", "5.0"))
    HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "10.0"))
    QUEUE_MAXSIZE = int(os.getenv("QUEUE_MAXSIZE", "100"))
    RETRY_TOTAL = int(os.getenv("RETRY_TOTAL", "5"))
    RETRY_BACKOFF_FACTOR = float(os.getenv("RETRY_BACKOFF_FACTOR", "1.0"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


if __name__ == "__main__":
    print("Endpoint:", AppConfig.ENDPOINT_URL)
    print("Serial port:", AppConfig.SERIAL_PORT)
