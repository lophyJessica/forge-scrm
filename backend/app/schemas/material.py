"""资料库 Schema（模块 01）。"""

from datetime import date, datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import MaterialStatus, SourceType, TrustLevel


# ---------------- 分类 ----------------

class MaterialClassCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    parent_id: int | None = None
    sort: int | None = 0


class MaterialClassUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=50)
    parent_id: int | None = None
    sort: int | None = None


class MaterialClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    parent_id: int | None = None
    sort: int | None = None
    created_at: datetime


# ---------------- 标签 ----------------

class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    group_name: str | None = Field(None, max_length=50, description="可选，一期不强制分组（D1）")


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    group_name: str | None = None
    created_at: datetime


# ---------------- 资料 ----------------

class MaterialBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    class_id: int
    source_type: SourceType
    source_url: str | None = Field(None, max_length=500)
    trust_level: TrustLevel
    # 有效期：页面已不展示/不填（2026-08-26 用户决定），保留数据库字段，
    # 创建时给默认值（当天 ~ +365天）满足非空约束
    valid_from: date = Field(default_factory=date.today)
    valid_until: date = Field(default_factory=lambda: date.today() + timedelta(days=365))


class MaterialCreate(MaterialBase):
    tags: list[str] = Field(default_factory=list, description="标签名列表；不存在则自动新建（D1）")
    submit_for_review: bool = Field(False, description="true=直接进入待审核；false=存为草稿")


class MaterialUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    content: str | None = Field(None, min_length=1)
    class_id: int | None = None
    source_type: SourceType | None = None
    source_url: str | None = Field(None, max_length=500)
    trust_level: TrustLevel | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    tags: list[str] | None = None


class MaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    class_id: int
    class_name: str | None = None
    source_type: SourceType
    source_url: str | None = None
    trust_level: TrustLevel
    valid_from: date
    valid_until: date
    status: MaterialStatus
    is_ai_product: bool
    source_analysis_task_id: int | None = None
    reviewer_id: int | None = None
    reviewed_at: datetime | None = None
    created_by: int
    created_at: datetime
    tags: list[str] = []


class MaterialReview(BaseModel):
    approved: bool = Field(..., description="true=通过（已生效）；false=驳回（已废弃）")


class MaterialComboQuery(BaseModel):
    """固定组合引用（M06）：按分类名组合生成引用预览。"""

    class_names: list[str] = Field(..., min_length=1)
    limit_per_class: int = Field(5, ge=1, le=50)


class MaterialComboPreviewItem(BaseModel):
    class_name: str
    materials: list[MaterialOut]


class MaterialComboPreview(BaseModel):
    items: list[MaterialComboPreviewItem]
    preview_text: str


class ImportRowError(BaseModel):
    row: int = Field(..., description="CSV 数据行号（含表头计数，从 2 开始）")
    message: str


class ImportResult(BaseModel):
    total_rows: int
    success: int
    failed: int
    errors: list[ImportRowError] = []
    stored_file: str = Field("", description="原文件本地留档路径（D-T4）")
    created_ids: list[int] = []
