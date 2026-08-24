"""资料库服务：惰性过期判断、标签解析、输出装配。"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import MaterialStatus
from app.models.material import Material, MaterialTag, Tag
from app.schemas.material import MaterialOut


def apply_lazy_expiry(db: Session, materials: list[Material]) -> None:
    """D-T3 惰性过期：读取/展示时判断有效期止，已生效且过期的置为「已过期」。

    不做定时扫描任务（红线：一期禁止定时任务）。
    """
    today = date.today()
    changed = False
    for m in materials:
        if m.status == MaterialStatus.已生效 and m.valid_until and m.valid_until < today:
            m.status = MaterialStatus.已过期
            changed = True
    if changed:
        db.commit()


def resolve_tags(db: Session, tag_names: list[str], created_by: int) -> list[Tag]:
    """标签自由创建（R12/D1）：不存在则页内直接新建。"""
    result: list[Tag] = []
    for raw in tag_names:
        name = (raw or "").strip()
        if not name:
            continue
        tag = db.scalar(select(Tag).where(Tag.name == name))
        if tag is None:
            tag = Tag(name=name, group_name=None, created_by=created_by)
            db.add(tag)
            db.flush()
        if tag not in result:
            result.append(tag)
    return result


def set_material_tags(db: Session, material: Material, tags: list[Tag]) -> None:
    db.query(MaterialTag).filter(MaterialTag.material_id == material.id).delete()
    db.flush()
    for tag in tags:
        db.add(MaterialTag(material_id=material.id, tag_id=tag.id))
    db.flush()


def to_out(db: Session, material: Material) -> MaterialOut:
    tag_names = [
        row.name
        for row in db.scalars(
            select(Tag)
            .join(MaterialTag, MaterialTag.tag_id == Tag.id)
            .where(MaterialTag.material_id == material.id)
            .order_by(Tag.id)
        ).all()
    ]
    out = MaterialOut.model_validate(material)
    out.tags = tag_names
    out.class_name = material.material_class.name if material.material_class else None
    return out
