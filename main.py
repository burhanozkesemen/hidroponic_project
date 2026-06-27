import logging
import queue
import signal
import threading
import time
from typing import Dict

import requests
import serial
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from config import AppConfig


logger = logging.getLogger("edge_gateway")


EXPECTED_KEYS = {"WT", "AT", "H", "PH", "TDS", "CO2", "WL"}


class SerialReader(threading.Thread):
    def __init__(self, data_queue: queue.Queue, stop_event: threading.Event) -> None:
        super().__init__(name="SerialReader", daemon=True)
        self.data_queue = data_queue
        self.stop_event = stop_event
        self.serial_port = AppConfig.SERIAL_PORT
        self.baud_rate = AppConfig.BAUD_RATE
        self.timeout = AppConfig.SERIAL_TIMEOUT
        self.reconnect_interval = AppConfig.SERIAL_RECONNECT_INTERVAL
        self.ser = None

    def open_serial(self) -> None:
        if self.ser and self.ser.is_open:
            return

        try:
            self.ser = serial.Serial(
                port=self.serial_port,
                baudrate=self.baud_rate,
                timeout=self.timeout,
            )
            logger.info("Serial port opened: %s @ %s", self.serial_port, self.baud_rate)
        except serial.SerialException as exc:
            self.ser = None
            raise

    def close_serial(self) -> None:
        if self.ser is not None and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                logger.exception("Failed to close serial port")
        self.ser = None

    def run(self) -> None:
        logger.info("Starting serial listener thread")
        while not self.stop_event.is_set():
            try:
                if self.ser is None or not self.ser.is_open:
                    self.open_serial()

                raw_line = self.ser.readline().decode("utf-8", errors="ignore").strip()
                if raw_line:
                    payload = self.parse_line(raw_line)
                    self.enqueue_payload(payload)
                else:
                    time.sleep(0.1)
            except serial.SerialException:
                logger.exception("Serial port error; reconnecting in %s seconds", self.reconnect_interval)
                self.close_serial()
                time.sleep(self.reconnect_interval)
            except ValueError as exc:
                logger.warning("Invalid serial payload ignored: %s", exc)
            except Exception:
                logger.exception("Unexpected error in serial thread")
                time.sleep(1)

        self.close_serial()
        logger.info("Serial listener thread stopped")

    def enqueue_payload(self, payload: Dict) -> None:
        try:
            self.data_queue.put(payload, block=False)
        except queue.Full:
            logger.warning("Data queue full, dropping payload: %s", payload)

    @staticmethod
    def parse_line(raw_line: str) -> Dict:
        segments = [segment.strip() for segment in raw_line.split("|") if segment.strip()]
        if len(segments) < len(EXPECTED_KEYS):
            raise ValueError("Incomplete payload")

        parsed = {}
        for segment in segments:
            if ":" not in segment:
                raise ValueError(f"Invalid segment format: {segment}")
            key, value = segment.split(":", 1)
            key = key.strip().upper()
            value = value.strip()
            if key not in EXPECTED_KEYS:
                raise ValueError(f"Unexpected key: {key}")
            if value == "":
                raise ValueError(f"Empty value for key: {key}")

            if key in {"WT", "AT", "H", "PH"}:
                parsed[key] = float(value)
            else:
                parsed[key] = int(float(value))

        missing = EXPECTED_KEYS - set(parsed.keys())
        if missing:
            raise ValueError(f"Missing keys: {sorted(missing)}")

        return {
            "water_temperature": parsed["WT"],
            "air_temperature": parsed["AT"],
            "humidity": parsed["H"],
            "ph": parsed["PH"],
            "tds": parsed["TDS"],
            "co2": parsed["CO2"],
            "water_level_low": bool(parsed["WL"]),
        }


class HttpSender(threading.Thread):
    def __init__(self, data_queue: queue.Queue, stop_event: threading.Event) -> None:
        super().__init__(name="HttpSender", daemon=True)
        self.data_queue = data_queue
        self.stop_event = stop_event
        self.endpoint = AppConfig.ENDPOINT_URL
        self.timeout = AppConfig.HTTP_TIMEOUT
        self.session = self.create_session()

    @staticmethod
    def create_session() -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=AppConfig.RETRY_TOTAL,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
            backoff_factor=AppConfig.RETRY_BACKOFF_FACTOR,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def run(self) -> None:
        logger.info("Starting HTTP sender thread")
        pending_payload = None
        while not self.stop_event.is_set():
            try:
                if pending_payload is None:
                    pending_payload = self.data_queue.get(timeout=0.5)

                if self.post_payload(pending_payload):
                    logger.info("Payload delivered: %s", pending_payload)
                    pending_payload = None
                    self.data_queue.task_done()
                else:
                    time.sleep(AppConfig.RETRY_BACKOFF_FACTOR)
            except queue.Empty:
                continue
            except Exception:
                logger.exception("Unexpected error in HTTP sender thread")
                time.sleep(1)

        logger.info("HTTP sender thread stopped")

    def post_payload(self, payload: Dict) -> bool:
        try:
            response = self.session.post(self.endpoint, json=payload, timeout=self.timeout)
            if 200 <= response.status_code < 300:
                return True

            if 400 <= response.status_code < 500 and response.status_code != 429:
                logger.error(
                    "Permanent error from endpoint %s status=%s response=%s",
                    self.endpoint,
                    response.status_code,
                    response.text,
                )
                return True

            logger.warning(
                "Transient endpoint failure status=%s response=%s",
                response.status_code,
                response.text,
            )
            return False
        except requests.RequestException:
            logger.exception("HTTP request failed, will retry")
            return False


def install_signal_handlers(stop_event: threading.Event) -> None:
    def handle_signal(signum, frame):
        logger.info("Shutdown signal received: %s", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)


def main() -> None:
    logging.basicConfig(
        level=getattr(logging, AppConfig.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    stop_event = threading.Event()
    install_signal_handlers(stop_event)

    data_queue: queue.Queue = queue.Queue(maxsize=AppConfig.QUEUE_MAXSIZE)
    serial_reader = SerialReader(data_queue, stop_event)
    http_sender = HttpSender(data_queue, stop_event)

    serial_reader.start()
    http_sender.start()

    try:
        while not stop_event.is_set():
            time.sleep(0.5)
    except KeyboardInterrupt:
        stop_event.set()

    serial_reader.join()
    http_sender.join()
    logger.info("Edge gateway stopped")


if __name__ == "__main__":
    main()
