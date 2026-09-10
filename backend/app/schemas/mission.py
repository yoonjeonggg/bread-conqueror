from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.enums import MissionMetric


class MissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    title: str
    description: str
    metric: MissionMetric
    target: int
    reward_exp: int
    progress: int
    completed: bool
    claimed: bool


class WeeklyMissionsOut(BaseModel):
    week_start: date
    missions: list[MissionOut]


class ClaimResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    reward_exp: int
    exp: int
    tier_level: int
    tier_changed: bool
