"""资料库路由（模块 01）：分类 / 标签 / 资料 CRUD / 搜索 / 固定组合引用 / 审核 / CSV 导入。"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, or_, select

from app.models.user import User
from app.core.deps import (
    AdminUser,
    CurrentUser,
    DbSession,
    allowed_material_class_ids,
    assert_material_class_visible,
    has_permission,
    require_permission,
)
from app.core.enums import MaterialStatus, Permission, SourceType, TrustLevel
from app.core.exceptions import BizError, forbidden, not_found
from app.core.logging import get_logger
from app.models.base import utcnow
from app.models.material import Material, MaterialClass, MaterialTag, Tag
from app.schemas.common import OkResult, PageResult
from app.schemas.material import (
    ImportResult,
    ImportRowError,
    MaterialClassCreate,
    MaterialClassOut,
    MaterialClassUpdate,
    MaterialComboPreview,
    MaterialComboPreviewItem,
    MaterialComboQuery,
    MaterialCreate,
    MaterialOut,
    MaterialReview,
    MaterialUpdate,
    TagCreate,
    TagOut,
)
from app.services import material_service as svc
from app.utils.csv_io import build_template, read_headers, sniff_rows, store_original

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["资料库"])

# CSV 固定模板列（D-T2）
MATERIAL_CSV_HEADERS = [
    "标题",
    "内容",
    "分类",
    "标签",
    "来源类型",
    "来源链接",
    "可信度",
    "有效期起",
    "有效期止",
]
MATERIAL_CSV_REQUIRED = ["标题", "内容", "分类", "来源类型", "可信度", "有效期起", "有效期止"]


# ==================== 资料分类 ====================

@router.get("/material-classes", response_model=list[MaterialClassOut], summary="资料分类列表")
def list_classes(current_user: CurrentUser, db: DbSession) -> list[MaterialClassOut]:
    stmt = select(MaterialClass).order_by(MaterialClass.created_at.desc(), MaterialClass.id.desc())
    allowed = allowed_material_class_ids(current_user)
    if allowed is not None:
        stmt = stmt.where(MaterialClass.id.in_(allowed or [-1]))
    return [MaterialClassOut.model_validate(c) for c in db.scalars(stmt).all()]


@router.post("/material-classes", response_model=MaterialClassOut, summary="新建分类（仅管理员）")
def create_class(payload: MaterialClassCreate, _: AdminUser, db: DbSession) -> MaterialClassOut:
    if db.scalar(select(MaterialClass).where(MaterialClass.name == payload.name)):
        raise BizError("分类名已存在")
    obj = MaterialClass(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return MaterialClassOut.model_validate(obj)


@router.put("/material-classes/{class_id}", response_model=MaterialClassOut, summary="修改分类（仅管理员）")
def update_class(
    class_id: int, payload: MaterialClassUpdate, _: AdminUser, db: DbSession
) -> MaterialClassOut:
    obj = db.get(MaterialClass, class_id)
    if not obj:
        raise not_found("资料分类")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] != obj.name:
        if db.scalar(select(MaterialClass).where(MaterialClass.name == data["name"])):
            raise BizError("分类名已存在")
    for k, v in data.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return MaterialClassOut.model_validate(obj)


@router.delete("/material-classes/{class_id}", response_model=OkResult, summary="删除分类（仅管理员）")
def delete_class(class_id: int, _: AdminUser, db: DbSession) -> OkResult:
    obj = db.get(MaterialClass, class_id)
    if not obj:
        raise not_found("资料分类")
    if db.scalar(select(func.count()).select_from(Material).where(Material.class_id == class_id)):
        raise BizError("该分类下仍有资料，无法删除")
    db.delete(obj)
    db.commit()
    return OkResult(message="分类已删除")


# ==================== 标签 ====================

@router.get("/tags", response_model=list[TagOut], summary="标签列表")
def list_tags(
    current_user: CurrentUser, db: DbSession, keyword: str | None = None
) -> list[TagOut]:
    stmt = select(Tag).order_by(Tag.created_at.desc(), Tag.id.desc())
    if keyword:
        stmt = stmt.where(Tag.name.like(f"%{keyword}%"))
    return [TagOut.model_validate(t) for t in db.scalars(stmt).all()]


@router.post("/tags", response_model=TagOut, summary="新建标签（自由创建，标签组可选 D1）")
def create_tag(
    payload: TagCreate,
    db: DbSession,
    current_user: User = Depends(require_permission(Permission.标签创建)),
) -> TagOut:
    existing = db.scalar(select(Tag).where(Tag.name == payload.name))
    if existing:
        return TagOut.model_validate(existing)
    tag = Tag(name=payload.name, group_name=payload.group_name, created_by=current_user.id)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return TagOut.model_validate(tag)


# ==================== 资料 CSV 模板 / 导入 ====================

@router.get("/materials/csv-template", summary="下载资料导入固定模板（D-T2）")
def material_csv_template(_: CurrentUser) -> Response:
    sample = [
        [
            "示例：制造业获客的三个结论",
            "正文内容，可含换行请用引号包裹",
            "商业研究结论",
            "制造业客户|获客",
            "报告",
            "https://example.com/report",
            "高",
            "2026-01-01",
            "2026-12-31",
        ]
    ]
    content = build_template(MATERIAL_CSV_HEADERS, sample)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="material_import_template.csv"'},
    )


@router.post("/materials/import", response_model=ImportResult, summary="CSV/TXT 导入资料（按固定模板）")
def import_materials(
    db: DbSession,
    current_user: CurrentUser,
    file: UploadFile = File(..., description="按模板导出的 CSV/TXT"),
) -> ImportResult:
    raw = file.file.read()
    if not raw:
        raise BizError("文件为空")

    try:
        headers = read_headers(raw)
        rows = sniff_rows(raw)
    except ValueError as exc:
        raise BizError(str(exc))

    missing = [c for c in MATERIAL_CSV_REQUIRED if c not in headers]
    if missing:
        raise BizError(f"模板列名不匹配，缺少必需列：{', '.join(missing)}")

    stored = store_original(raw, file.filename or "material.csv", "material")

    class_map = {c.name: c for c in db.scalars(select(MaterialClass)).all()}
    errors: list[ImportRowError] = []
    created_ids: list[int] = []

    for idx, row in enumerate(rows, start=2):
        try:
            title = row.get("标题", "").strip()
            content = row.get("内容", "").strip()
            class_name = row.get("分类", "").strip()
            if not title:
                raise ValueError("标题为空")
            if not content:
                raise ValueError("内容为空")
            klass = class_map.get(class_name)
            if klass is None:
                raise ValueError(f"分类「{class_name}」不存在")
            assert_material_class_visible(current_user, klass.id)

            source_type = row.get("来源类型", "").strip()
            if source_type not in [e.value for e in SourceType]:
                raise ValueError(f"来源类型「{source_type}」不在枚举内")
            trust = row.get("可信度", "").strip()
            if trust not in [e.value for e in TrustLevel]:
                raise ValueError(f"可信度「{trust}」不在枚举内")

            try:
                valid_from = date.fromisoformat(row.get("有效期起", "").strip())
                valid_until = date.fromisoformat(row.get("有效期止", "").strip())
            except ValueError:
                raise ValueError("有效期格式错误，应为 YYYY-MM-DD")
            if valid_until < valid_from:
                raise ValueError("有效期止早于有效期起")

            material = Material(
                title=title,
                content=content,
                class_id=klass.id,
                source_type=SourceType(source_type),
                source_url=(row.get("来源链接") or "").strip() or None,
                trust_level=TrustLevel(trust),
                valid_from=valid_from,
                valid_until=valid_until,
                status=MaterialStatus.待审核,
                is_ai_product=False,
                created_by=current_user.id,
            )
            db.add(material)
            db.flush()

            tag_names = [t for t in (row.get("标签") or "").replace(",", "|").split("|") if t.strip()]
            if tag_names:
                tags = svc.resolve_tags(db, tag_names, current_user.id)
                svc.set_material_tags(db, material, tags)
            created_ids.append(material.id)
        except Exception as exc:  # 单行失败不影响其他行
            db.rollback()
            errors.append(ImportRowError(row=idx, message=str(exc)))

    db.commit()
    logger.info("资料导入：成功 %s 行，失败 %s 行，原文件 %s", len(created_ids), len(errors), stored)
    return ImportResult(
        total_rows=len(rows),
        success=len(created_ids),
        failed=len(errors),
        errors=errors,
        stored_file=stored,
        created_ids=created_ids,
    )


# ==================== 固定组合引用 ====================

@router.post("/materials/combo-preview", response_model=MaterialComboPreview, summary="固定组合引用预览（M06）")
def combo_preview(
    payload: MaterialComboQuery, current_user: CurrentUser, db: DbSession
) -> MaterialComboPreview:
    allowed = allowed_material_class_ids(current_user)
    items: list[MaterialComboPreviewItem] = []
    lines: list[str] = []
    for class_name in payload.class_names:
        klass = db.scalar(select(MaterialClass).where(MaterialClass.name == class_name))
        if klass is None:
            raise BizError(f"分类「{class_name}」不存在")
        if allowed is not None and klass.id not in allowed:
            continue
        stmt = (
            select(Material)
            .where(Material.class_id == klass.id, Material.status == MaterialStatus.已生效)
            .order_by(Material.created_at.desc(), Material.id.desc())
            .limit(payload.limit_per_class)
        )
        rows = list(db.scalars(stmt).all())
        svc.apply_lazy_expiry(db, rows)
        rows = [r for r in rows if r.status == MaterialStatus.已生效]
        outs = [svc.to_out(db, r) for r in rows]
        items.append(MaterialComboPreviewItem(class_name=class_name, materials=outs))
        lines.append(f"【{class_name}】")
        lines.extend(f"- {o.title}：{o.content[:120]}" for o in outs)
    return MaterialComboPreview(items=items, preview_text="\n".join(lines))


# ==================== 资料 CRUD ====================

@router.get("/materials", response_model=PageResult[MaterialOut], summary="资料搜索（分类/标签/关键词）")
def list_materials(
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    class_id: int | None = None,
    status: MaterialStatus | None = None,
    tag: str | None = Query(None, description="标签名"),
    keyword: str | None = Query(None, description="标题/正文关键词"),
    is_ai_product: bool | None = None,
) -> PageResult[MaterialOut]:
    stmt = select(Material)
    allowed = allowed_material_class_ids(current_user)
    if allowed is not None:
        stmt = stmt.where(Material.class_id.in_(allowed or [-1]))
    if class_id is not None:
        stmt = stmt.where(Material.class_id == class_id)
    if status is not None:
        stmt = stmt.where(Material.status == status)
    if is_ai_product is not None:
        stmt = stmt.where(Material.is_ai_product.is_(is_ai_product))
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(Material.title.like(like), Material.content.like(like)))
    if tag:
        stmt = stmt.where(
            Material.id.in_(
                select(MaterialTag.material_id)
                .join(Tag, Tag.id == MaterialTag.tag_id)
                .where(Tag.name == tag)
            )
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = list(
        db.scalars(
            stmt.order_by(Material.created_at.desc(), Material.id.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
    )
    svc.apply_lazy_expiry(db, rows)
    return PageResult[MaterialOut](
        total=total,
        page=page,
        page_size=page_size,
        items=[svc.to_out(db, r) for r in rows],
    )


@router.post("/materials", response_model=MaterialOut, summary="新增资料（保存草稿或提交审核）")
def create_material(
    payload: MaterialCreate, current_user: CurrentUser, db: DbSession
) -> MaterialOut:
    klass = db.get(MaterialClass, payload.class_id)
    if not klass:
        raise not_found("资料分类")
    assert_material_class_visible(current_user, payload.class_id)
    if payload.valid_until < payload.valid_from:
        raise BizError("有效期止不能早于有效期起")
    if payload.tags and not has_permission(current_user, Permission.标签创建):
        existing = {t.name for t in db.scalars(select(Tag)).all()}
        new_tags = [t for t in payload.tags if t.strip() and t.strip() not in existing]
        if new_tags:
            raise forbidden("缺少功能权限：标签创建")

    material = Material(
        **payload.model_dump(exclude={"tags", "submit_for_review"}),
        status=MaterialStatus.待审核 if payload.submit_for_review else MaterialStatus.草稿,
        is_ai_product=False,
        created_by=current_user.id,
    )
    db.add(material)
    db.flush()
    if payload.tags:
        svc.set_material_tags(db, material, svc.resolve_tags(db, payload.tags, current_user.id))
    db.commit()
    db.refresh(material)
    return svc.to_out(db, material)


@router.get("/materials/{material_id}", response_model=MaterialOut, summary="资料详情")
def get_material(material_id: int, current_user: CurrentUser, db: DbSession) -> MaterialOut:
    material = db.get(Material, material_id)
    if not material:
        raise not_found("资料")
    assert_material_class_visible(current_user, material.class_id)
    svc.apply_lazy_expiry(db, [material])
    return svc.to_out(db, material)


@router.put("/materials/{material_id}", response_model=MaterialOut, summary="修改资料")
def update_material(
    material_id: int, payload: MaterialUpdate, current_user: CurrentUser, db: DbSession
) -> MaterialOut:
    material = db.get(Material, material_id)
    if not material:
        raise not_found("资料")
    assert_material_class_visible(current_user, material.class_id)
    data = payload.model_dump(exclude_unset=True, exclude={"tags"})
    if "class_id" in data:
        if not db.get(MaterialClass, data["class_id"]):
            raise not_found("资料分类")
        assert_material_class_visible(current_user, data["class_id"])
    for k, v in data.items():
        setattr(material, k, v)
    if material.valid_until < material.valid_from:
        raise BizError("有效期止不能早于有效期起")
    if payload.tags is not None:
        svc.set_material_tags(db, material, svc.resolve_tags(db, payload.tags, current_user.id))
    db.commit()
    db.refresh(material)
    svc.apply_lazy_expiry(db, [material])
    return svc.to_out(db, material)


@router.post("/materials/{material_id}/submit", response_model=MaterialOut, summary="提交审核（草稿→待审核）")
def submit_material(material_id: int, current_user: CurrentUser, db: DbSession) -> MaterialOut:
    material = db.get(Material, material_id)
    if not material:
        raise not_found("资料")
    assert_material_class_visible(current_user, material.class_id)
    if material.status != MaterialStatus.草稿:
        raise BizError(f"当前状态「{material.status.value}」不可提交审核")
    material.status = MaterialStatus.待审核
    db.commit()
    db.refresh(material)
    return svc.to_out(db, material)


@router.post("/materials/{material_id}/review", response_model=MaterialOut, summary="资料审核（R1：审核后才能使用）")
def review_material(
    material_id: int, payload: MaterialReview, current_user: CurrentUser, db: DbSession
) -> MaterialOut:
    material = db.get(Material, material_id)
    if not material:
        raise not_found("资料")
    assert_material_class_visible(current_user, material.class_id)
    if material.status != MaterialStatus.待审核:
        raise BizError(f"当前状态「{material.status.value}」不可审核")
    material.status = MaterialStatus.已生效 if payload.approved else MaterialStatus.已废弃
    material.reviewer_id = current_user.id
    material.reviewed_at = utcnow()
    db.commit()
    db.refresh(material)
    svc.apply_lazy_expiry(db, [material])
    return svc.to_out(db, material)


@router.post("/materials/{material_id}/disable", response_model=MaterialOut, summary="停用资料（已生效→已停用）")
def disable_material(material_id: int, current_user: CurrentUser, db: DbSession) -> MaterialOut:
    material = db.get(Material, material_id)
    if not material:
        raise not_found("资料")
    assert_material_class_visible(current_user, material.class_id)
    if material.status != MaterialStatus.已生效:
        raise BizError(f"当前状态「{material.status.value}」不可停用")
    material.status = MaterialStatus.已停用
    db.commit()
    db.refresh(material)
    return svc.to_out(db, material)


@router.post("/materials/{material_id}/enable", response_model=MaterialOut, summary="重新启用资料（已停用→已生效）")
def enable_material(material_id: int, current_user: CurrentUser, db: DbSession) -> MaterialOut:
    material = db.get(Material, material_id)
    if not material:
        raise not_found("资料")
    assert_material_class_visible(current_user, material.class_id)
    if material.status != MaterialStatus.已停用:
        raise BizError(f"当前状态「{material.status.value}」不可启用")
    material.status = MaterialStatus.已生效
    db.commit()
    db.refresh(material)
    svc.apply_lazy_expiry(db, [material])
    return svc.to_out(db, material)


@router.post("/materials/{material_id}/discard", response_model=MaterialOut, summary="确认废弃（已过期→已废弃）")
def discard_material(material_id: int, current_user: CurrentUser, db: DbSession) -> MaterialOut:
    material = db.get(Material, material_id)
    if not material:
        raise not_found("资料")
    assert_material_class_visible(current_user, material.class_id)
    svc.apply_lazy_expiry(db, [material])
    if material.status != MaterialStatus.已过期:
        raise BizError(f"当前状态「{material.status.value}」不可确认废弃")
    material.status = MaterialStatus.已废弃
    db.commit()
    db.refresh(material)
    return svc.to_out(db, material)


@router.delete("/materials/{material_id}", response_model=OkResult, summary="删除资料（成员需授权）")
def delete_material(
    material_id: int,
    db: DbSession,
    current_user: User = Depends(require_permission(Permission.资料删除)),
) -> OkResult:
    material = db.get(Material, material_id)
    if not material:
        raise not_found("资料")
    assert_material_class_visible(current_user, material.class_id)
    db.delete(material)
    db.commit()
    return OkResult(message="资料已删除")
