"""Rule-based abuse scoring (F-CONQ-09).

Kept deliberately simple and side-effect free: callers pass in the previous flag
context and get back a decision. Thresholds come from policy_configs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.services.geo_service import speed_kmh


@dataclass(frozen=True)
class AbuseSignal:
    is_suspicious: bool
    score: float
    reasons: list[str]


def evaluate_conquest(
    *,
    new_lat: float,
    new_lng: float,
    new_time: datetime,
    prev_lat: float | None,
    prev_lng: float | None,
    prev_time: datetime | None,
    max_speed_kmh: float,
) -> AbuseSignal:
    reasons: list[str] = []
    score = 0.0

    if prev_lat is not None and prev_lng is not None and prev_time is not None:
        seconds = (new_time - prev_time).total_seconds()
        v = speed_kmh(prev_lat, prev_lng, new_lat, new_lng, seconds)
        if v > max_speed_kmh:
            score += 0.7
            reasons.append(
                f"이동 속도 {v:.0f}km/h 로 임계값({max_speed_kmh:.0f}) 초과"
            )
        if 0 <= seconds < 60:
            score += 0.2
            reasons.append("직전 정복과 60초 이내 연속 발생")

    return AbuseSignal(is_suspicious=score >= 0.7, score=round(score, 2), reasons=reasons)
