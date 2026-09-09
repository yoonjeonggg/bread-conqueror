"""EXIF extraction for silver-flag evidence (F-CONQ-05).

Used to grade silver-flag trust: a photo carrying a plausible capture time and
GPS tag counts for more than a bare claim.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime

import exifread


@dataclass(frozen=True)
class ExifInfo:
    captured_at: datetime | None
    lat: float | None
    lng: float | None

    @property
    def has_gps(self) -> bool:
        return self.lat is not None and self.lng is not None


def _ratio_to_float(values) -> float:
    d, m, s = (v.num / v.den for v in values.values)
    return d + m / 60 + s / 3600


def extract(data: bytes) -> ExifInfo:
    tags = exifread.process_file(io.BytesIO(data), details=False)

    captured_at: datetime | None = None
    raw_dt = tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTime")
    if raw_dt is not None:
        try:
            captured_at = datetime.strptime(str(raw_dt), "%Y:%m:%d %H:%M:%S")
        except ValueError:
            captured_at = None

    lat = lng = None
    if "GPS GPSLatitude" in tags and "GPS GPSLongitude" in tags:
        lat = _ratio_to_float(tags["GPS GPSLatitude"])
        lng = _ratio_to_float(tags["GPS GPSLongitude"])
        if str(tags.get("GPS GPSLatitudeRef", "N")) == "S":
            lat = -lat
        if str(tags.get("GPS GPSLongitudeRef", "E")) == "W":
            lng = -lng

    return ExifInfo(captured_at=captured_at, lat=lat, lng=lng)
