from __future__ import annotations

from typing import Dict


class SensorParseError(ValueError):
    """Raised when a serial payload cannot be parsed into a valid sensor dictionary."""


EXPECTED_KEYS = {
    "WT",
    "AT",
    "H",
    "PH",
    "TDS",
    "CO2",
    "WL",
}

FIELD_MAPPING = {
    "WT": "water_temperature",
    "AT": "air_temperature",
    "H": "humidity",
    "PH": "ph",
    "TDS": "tds",
    "CO2": "co2",
    "WL": "water_level_low",
}

TYPE_MAPPING = {
    "WT": float,
    "AT": float,
    "H": float,
    "PH": float,
    "TDS": int,
    "CO2": int,
    "WL": int,
}


def parse_sensor_payload(raw_line: str) -> Dict[str, object]:
    """Parse a raw serial payload into a validated sensor dictionary.

    The accepted input format is:
        WT:0.0|AT:25.4|H:60.2|PH:6.75|TDS:2850|CO2:1850|WL:1

    Returns a JSON-serializable dictionary ready for Azure IoT telemetry.
    """
    if not raw_line or not raw_line.strip():
        raise SensorParseError("Empty sensor payload received")

    parts = [segment.strip() for segment in raw_line.split("|") if segment.strip()]
    if not parts:
        raise SensorParseError("Sensor payload contains no data fields")

    parsed_values: Dict[str, object] = {}
    received_keys = set()

    for part in parts:
        if ":" not in part:
            raise SensorParseError(f"Invalid token without separator: {part}")

        key, value = part.split(":", 1)
        key = key.strip().upper()
        value = value.strip()

        if key not in EXPECTED_KEYS:
            raise SensorParseError(f"Unexpected sensor key: {key}")

        if value == "":
            raise SensorParseError(f"Missing value for key: {key}")

        try:
            typed_value = TYPE_MAPPING[key](value)
        except ValueError as exc:
            raise SensorParseError(f"Invalid value for {key}: {value}") from exc

        parsed_values[key] = typed_value
        received_keys.add(key)

    missing_keys = EXPECTED_KEYS - received_keys
    if missing_keys:
        raise SensorParseError(f"Missing required fields: {sorted(missing_keys)}")

    result: Dict[str, object] = {
        FIELD_MAPPING[key]: parsed_values[key] for key in FIELD_MAPPING
    }

    # Convert WL into a boolean meaning "water level is low".
    result["water_level_low"] = bool(parsed_values["WL"])

    return result
