"""业务方向 / 专业方向字典路由（选题生成页二级联动）。"""

from fastapi import APIRouter
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.core.exceptions import BizError, not_found
from app.models.direction import BusinessDirection, DirectionStatus, Specialty
from app.schemas.direction import (
    BusinessDirectionCreate,
    BusinessDirectionOut,
    DirectionsResponse,
    SpecialtyCreate,
    SpecialtyOut,
)

router = APIRouter(prefix="/api/directions", tags=["方向字典"])


@router.get("", response_model=DirectionsResponse, summary="获取全部 active 业务方向与专业方向")
def list_directions(_: CurrentUser, db: DbSession) -> DirectionsResponse:
    business_rows = db.scalars(
        select(BusinessDirection)
        .where(BusinessDirection.status == DirectionStatus.active)
        .order_by(BusinessDirection.id)
    ).all()
    specialty_rows = db.scalars(
        select(Specialty)
        .where(Specialty.status == DirectionStatus.active)
        .order_by(Specialty.business_direction_id, Specialty.id)
    ).all()
    return DirectionsResponse(
        business_directions=[BusinessDirectionOut.model_validate(r) for r in business_rows],
        specialties=[SpecialtyOut.model_validate(r) for r in specialty_rows],
    )


@router.post(
    "/business",
    response_model=BusinessDirectionOut,
    summary="新增业务方向（即建即用）",
)
def create_business_direction(
    payload: BusinessDirectionCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> BusinessDirectionOut:
    name = payload.name.strip()
    if not name:
        raise BizError("请输入 1-50 字符的业务方向名称")
    exists = db.scalar(select(BusinessDirection.id).where(BusinessDirection.name == name))
    if exists is not None:
        raise BizError("该业务方向已存在")
    row = BusinessDirection(
        name=name,
        status=DirectionStatus.active,
        created_by=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return BusinessDirectionOut.model_validate(row)


@router.post(
    "/specialties",
    response_model=SpecialtyOut,
    summary="新增专业方向（即建即用，挂业务方向下）",
)
def create_specialty(
    payload: SpecialtyCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> SpecialtyOut:
    name = payload.name.strip()
    if not name:
        raise BizError("请输入 1-50 字符的专业方向名称")
    parent = db.get(BusinessDirection, payload.business_direction_id)
    if not parent:
        raise not_found("业务方向")
    if parent.status != DirectionStatus.active:
        raise BizError("业务方向不可用")
    dup = db.scalar(
        select(Specialty.id).where(
            Specialty.business_direction_id == payload.business_direction_id,
            Specialty.name == name,
        )
    )
    if dup is not None:
        raise BizError("该专业方向已存在")
    row = Specialty(
        business_direction_id=payload.business_direction_id,
        name=name,
        status=DirectionStatus.active,
        created_by=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return SpecialtyOut.model_validate(row)
