"""元数据路由：把 context/05 定义的枚举下发给前端。

对应 context/05 §5 SSOT 规则：「所有枚举值以本文档为准，不在前端硬编码第二套」。
"""

from fastapi import APIRouter

from app.core import enums
from app.core.deps import CurrentUser

router = APIRouter(prefix="/api/meta", tags=["元数据"])

_ENUM_MAP = {
    "material_class_name": enums.MaterialClassName,
    "source_type": enums.SourceType,
    "trust_level": enums.TrustLevel,
    "material_status": enums.MaterialStatus,
    "prompt_task_type": enums.PromptTaskType,
    "prompt_status": enums.PromptStatus,
    "specialty": enums.Specialty,
    "topic_status": enums.TopicStatus,
    "screening_result": enums.ScreeningResult,
    "script_style": enums.ScriptStyle,
    "content_element": enums.ContentElement,
    "script_status": enums.ScriptStatus,
    "collection_method": enums.CollectionMethod,
    "business_object": enums.BusinessObject,
    "platform": enums.Platform,
    "data_source_status": enums.DataSourceStatus,
    "analysis_task_type": enums.AnalysisTaskType,
    "analysis_task_status": enums.AnalysisTaskStatus,
    "writeback_material_status": enums.WritebackMaterialStatus,
    "writeback_topic_status": enums.WritebackTopicStatus,
    "user_role": enums.UserRole,
    "user_status": enums.UserStatus,
    "data_scope_type": enums.DataScopeType,
}


@router.get("/enums", summary="全部业务枚举（前端不得再硬编码第二套）")
def get_enums(_: CurrentUser) -> dict[str, list[str]]:
    return {key: [e.value for e in cls] for key, cls in _ENUM_MAP.items()}


@router.get("/permissions", summary="功能权限字典（code + 中文名）")
def get_permissions(_: CurrentUser) -> list[dict[str, str]]:
    return [{"code": p.value, "label": p.name} for p in enums.Permission]
