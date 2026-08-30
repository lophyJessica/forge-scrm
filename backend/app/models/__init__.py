"""模型汇总导出。表清单严格对齐 prd-docs/核心字段清单.md（17 张表）。

不建表（文档已明确）：topic_version（D8 二期）、prompt_version（待确认）、material_version（待确认）。
"""

from app.models.analysis import (
    AnalysisResult,
    AnalysisResultMaterial,
    AnalysisResultTopic,
    AnalysisTask,
    AnalysisTaskInput,
    DataSource,
    RawData,
)
from app.models.base import Base
from app.models.material import Material, MaterialClass, MaterialTag, Tag
from app.models.prompt import PromptTemplate
from app.models.direction import BusinessDirection, Specialty
from app.models.script import Script, ScriptVersion
from app.models.topic import Topic, TopicMaterial
from app.models.user import User
from app.models.phase2 import (
    BenchmarkAccount,
    CollectionRecord,
    CollectionResult,
    CollectionTask,
    ResearchReference,
    ResearchReport,
    ResearchTask,
)
from app.models.report import Report, ReportPushRecord, ReportPushTask, ReportTemplate

__all__ = [
    "Base",
    "User",
    "MaterialClass",
    "Material",
    "Tag",
    "MaterialTag",
    "PromptTemplate",
    "BusinessDirection",
    "Specialty",
    "Topic",
    "TopicMaterial",
    "Script",
    "ScriptVersion",
    "DataSource",
    "RawData",
    "AnalysisTask",
    "AnalysisTaskInput",
    "AnalysisResult",
    "AnalysisResultMaterial",
    "AnalysisResultTopic",
    "BenchmarkAccount",
    "CollectionTask",
    "CollectionRecord",
    "CollectionResult",
    "ResearchTask",
    "ResearchReport",
    "ResearchReference",
    "Report",
    "ReportTemplate",
    "ReportPushTask",
    "ReportPushRecord",
]
