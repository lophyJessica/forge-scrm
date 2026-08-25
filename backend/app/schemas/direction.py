"""业务方向 / 专业方向 Schema（与前端 TopicGenerate 类型对齐）。"""

from pydantic import BaseModel, ConfigDict, Field


class BusinessDirectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class SpecialtyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_direction_id: int
    name: str


class DirectionsResponse(BaseModel):
    business_directions: list[BusinessDirectionOut]
    specialties: list[SpecialtyOut]


class BusinessDirectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)


class SpecialtyCreate(BaseModel):
    business_direction_id: int = Field(..., ge=1)
    name: str = Field(..., min_length=1, max_length=50)
