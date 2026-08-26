"""提示词模板路由（模块 04 配置项）。

权限：context/06 §2.2「提示词配置」——管理员恒有；成员须显式授权 Permission.提示词配置。
D9：一期不建 prompt_version 独立版本表，修改直接 version+1。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.models.user import User
from app.core.deps import CurrentUser, DbSession, require_permission
from app.core.enums import Permission, PromptStatus, PromptTaskType
from app.core.exceptions import BizError, not_found
from app.models.prompt import PromptTemplate
from app.schemas.common import OkResult, PageResult
from app.schemas.prompt import PromptTemplateCreate, PromptTemplateOut, PromptTemplateUpdate
from app.services.script_service import DEFAULT_SYSTEM_PROMPT as DEFAULT_SCRIPT_SYSTEM_PROMPT
from app.services.topic_service import DEFAULT_SYSTEM_PROMPT as DEFAULT_TOPIC_SYSTEM_PROMPT

router = APIRouter(prefix="/api/prompt-templates", tags=["提示词模板"])
v1_router = APIRouter(prefix="/api/v1/prompt-templates", tags=["提示词模板"])


@router.get("", response_model=PageResult[PromptTemplateOut], summary="提示词模板列表")
def list_templates(
    _: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    task_type: PromptTaskType | None = None,
    status: PromptStatus | None = None,
    keyword: str | None = None,
) -> PageResult[PromptTemplateOut]:
    stmt = select(PromptTemplate)
    if task_type is not None:
        stmt = stmt.where(PromptTemplate.task_type == task_type)
    if status is not None:
        stmt = stmt.where(PromptTemplate.status == status)
    if keyword:
        stmt = stmt.where(PromptTemplate.name.like(f"%{keyword}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(PromptTemplate.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return PageResult[PromptTemplateOut](
        total=total,
        page=page,
        page_size=page_size,
        items=[PromptTemplateOut.model_validate(r) for r in rows],
    )


@router.get("/builtin", response_model=list[dict[str, str]], summary="模板库默认模板")
@v1_router.get("/builtin", response_model=list[dict[str, str]], summary="模板库默认模板")
def list_builtin_templates(_: CurrentUser, db: DbSession) -> list[dict[str, str]]:
    """返回每个生成任务类型的首条模板；空表时回退代码常量。"""

    result: list[dict[str, str]] = []
    fallbacks = {
        PromptTaskType.选题生成: DEFAULT_TOPIC_SYSTEM_PROMPT,
        PromptTaskType.脚本生成: DEFAULT_SCRIPT_SYSTEM_PROMPT,
    }
    for task_type, fallback in fallbacks.items():
        template = db.scalar(
            select(PromptTemplate)
            .where(PromptTemplate.task_type == task_type)
            .order_by(PromptTemplate.id.asc())
        )
        result.append({"task_type": task_type.value, "content": template.content if template else fallback})
    return result


@router.post("", response_model=PromptTemplateOut, summary="新建提示词模板")
def create_template(
    payload: PromptTemplateCreate,
    db: DbSession,
    current_user: User = Depends(require_permission(Permission.提示词配置)),
) -> PromptTemplateOut:
    if payload.task_type in (PromptTaskType.资料分析, PromptTaskType.数据分析) and not payload.output_schema:
        raise BizError("分析类提示词必须定义 output_schema（结构化输出字段）")
    template = PromptTemplate(
        task_type=payload.task_type,
        name=payload.name,
        content=payload.content,
        version=1,
        material_combo=payload.material_combo,
        output_schema=payload.output_schema,
        status=payload.status,
        created_by=current_user.id,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return PromptTemplateOut.model_validate(template)


@router.get("/{template_id}", response_model=PromptTemplateOut, summary="提示词模板详情")
def get_template(template_id: int, _: CurrentUser, db: DbSession) -> PromptTemplateOut:
    template = db.get(PromptTemplate, template_id)
    if not template:
        raise not_found("提示词模板")
    return PromptTemplateOut.model_validate(template)


@router.put("/{template_id}", response_model=PromptTemplateOut, summary="修改提示词模板（version+1）")
def update_template(
    template_id: int,
    payload: PromptTemplateUpdate,
    db: DbSession,
    current_user: User = Depends(require_permission(Permission.提示词配置)),
) -> PromptTemplateOut:
    template = db.get(PromptTemplate, template_id)
    if not template:
        raise not_found("提示词模板")
    data = payload.model_dump(exclude_unset=True)
    content_changed = "content" in data and data["content"] != template.content
    for k, v in data.items():
        setattr(template, k, v)
    if content_changed:
        template.version = (template.version or 1) + 1
    db.commit()
    db.refresh(template)
    return PromptTemplateOut.model_validate(template)


@router.delete("/{template_id}", response_model=OkResult, summary="删除提示词模板")
def delete_template(
    template_id: int,
    db: DbSession,
    current_user: User = Depends(require_permission(Permission.提示词配置)),
) -> OkResult:
    template = db.get(PromptTemplate, template_id)
    if not template:
        raise not_found("提示词模板")
    remaining = db.scalar(
        select(func.count())
        .select_from(PromptTemplate)
        .where(PromptTemplate.task_type == template.task_type)
    ) or 0
    if remaining <= 1:
        raise BizError("该任务类型至少需要保留一条模板")
    db.delete(template)
    db.commit()
    return OkResult(message="提示词模板已删除")
