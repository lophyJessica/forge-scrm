"""枚举常量。

铁律：所有枚举值必须来自 `context/05-术语与字段口径.md` 与 `prd-docs/核心字段清单.md`，
不得在代码中新造文档未定义的枚举值（AGENTS.md 红线）。
"""

from enum import StrEnum


# ---------------- 资料库（context/05 §2、§4.1）----------------

class MaterialClassName(StrEnum):
    """资料分类枚举（context/05 §2）。material_class 为可扩展表，本枚举用于种子数据。"""

    商业研究结论 = "商业研究结论"
    案例包装 = "案例包装"
    评论和私信 = "评论和私信"
    个人观点 = "个人观点"
    对标账号分析 = "对标账号分析"
    相关热点 = "相关热点"


class SourceType(StrEnum):
    """资料来源类型（context/05 §4.1）。"""

    公众号 = "公众号"
    报告 = "报告"
    社交 = "社交"
    客户 = "客户"
    思考 = "思考"
    对标 = "对标"


class TrustLevel(StrEnum):
    """可信度（context/05 §4.1）。"""

    高 = "高"
    中 = "中"
    低 = "低"


class MaterialStatus(StrEnum):
    """资料状态机（context/04 §1）。"""

    草稿 = "草稿"
    待审核 = "待审核"
    已生效 = "已生效"
    已停用 = "已停用"
    已过期 = "已过期"
    已废弃 = "已废弃"


# ---------------- 提示词（context/05 §4.3）----------------

class PromptTaskType(StrEnum):
    """提示词模板任务类型（context/05 §4.3）。"""

    选题生成 = "选题生成"
    脚本生成 = "脚本生成"
    资料分析 = "资料分析"
    数据分析 = "数据分析"


class PromptStatus(StrEnum):
    """提示词启用状态（⚠️ 核心字段清单标注为新增建议字段，非阻塞业务字段）。"""

    启用 = "启用"
    停用 = "停用"


# ---------------- 选题（context/05 §3、§4.4）----------------

class Specialty(StrEnum):
    """专业方向（context/05 §3.1）。"""

    市场营销 = "市场营销"
    企业经营 = "企业经营"
    自媒体平台流量与规划算法逻辑 = "自媒体平台流量与规划算法逻辑"
    用户需求与痛点 = "用户需求与痛点"


class TopicStatus(StrEnum):
    """选题状态机（context/04 §2）；已选定/已使用为派生状态。"""

    待筛选 = "待筛选"
    已选定 = "已选定"
    已生成脚本 = "已生成脚本"
    已使用 = "已使用"
    已废弃 = "已废弃"


class ScreeningResult(StrEnum):
    """人工筛选结果（context/05 §4.4）。"""

    选中 = "选中"
    淘汰 = "淘汰"


# ---------------- 脚本（context/05 §4.5）----------------

class ScriptStyle(StrEnum):
    """语言风格（context/05 §4.5）。"""

    专业严谨 = "专业严谨"
    轻松口语 = "轻松口语"
    讲故事 = "讲故事"


class ContentElement(StrEnum):
    """内容要素（context/05 §4.5），以 JSON 数组存储。"""

    案例 = "案例"
    数据 = "数据"
    个人观点 = "个人观点"


class ScriptStatus(StrEnum):
    """脚本状态机（context/04 §3）；草稿为派生，已使用由人工标记（D4）。"""

    草稿 = "草稿"
    待审核 = "待审核"
    已通过 = "已通过"
    已使用 = "已使用"
    已废弃 = "已废弃"


# ---------------- 数据源 / 原始数据（context/05 §4.6）----------------

class CollectionMethod(StrEnum):
    """采集方式（context/05 §4.6，D5）。自动采集仅作架构预留，一期不实现采集逻辑。"""

    手动录入 = "手动录入"
    CSV导入 = "CSV 导入"
    自动采集 = "自动采集"  # 架构预留，一期不实现


class BusinessObject(StrEnum):
    """业务对象（context/05 §4.6）。"""

    自己账号 = "自己账号"
    对标账号 = "对标账号"
    行业报告 = "行业报告"
    相关热点 = "相关热点"
    评论和私信 = "评论和私信"


class Platform(StrEnum):
    """平台（context/05 §4.6）；非平台文本资料可为空。"""

    视频号 = "视频号"


class DataSourceStatus(StrEnum):
    """数据源启用状态（⚠️ 新增建议字段）。"""

    启用 = "启用"
    停用 = "停用"


# ---------------- 分析任务 / 结果（context/05 §4.7）----------------

class AnalysisTaskType(StrEnum):
    """分析任务类型。

    TODO 需人工确认：context/05 §4.7 仅写「指定分析任务」，未给出枚举值。
    此处沿用 context/05 §4.3 提示词任务类型中属于分析的两项，未新造文档外语义。
    """

    资料分析 = "资料分析"
    数据分析 = "数据分析"


class AnalysisTaskStatus(StrEnum):
    """分析任务状态机（context/04 §4）。"""

    待执行 = "待执行"
    执行中 = "执行中"
    已完成 = "已完成"
    失败 = "失败"
    待审核 = "待审核"
    已确认 = "已确认"
    已废弃 = "已废弃"


class WritebackMaterialStatus(StrEnum):
    """资料库回写状态（context/05 §4.7，独立动作）。"""

    未回写 = "未回写"
    已回写 = "已回写"


class WritebackTopicStatus(StrEnum):
    """选题反哺状态（context/05 §4.7，独立动作）。"""

    未反哺 = "未反哺"
    已反哺 = "已反哺"


# ---------------- 用户与权限（context/05 §4.8、context/06 §2.2）----------------

class UserRole(StrEnum):
    """角色（context/06 §2.4：存储枚举统一使用 管理员/成员）。"""

    管理员 = "管理员"
    成员 = "成员"


class UserStatus(StrEnum):
    """账号状态（context/05 §4.8）。"""

    启用 = "启用"
    停用 = "停用"


class DataScopeType(StrEnum):
    """数据范围类型（context/05 §4.8：全量/指定资料分类/指定数据源）。"""

    全量 = "全量"
    指定 = "指定"


class Permission(StrEnum):
    """功能权限码。

    对应 context/06 §2.2 权限矩阵中成员标注为「由管理员授权」或「待确认」的动作。
    这些动作成员默认无权，须由管理员显式授予（矩阵口径：「待确认」不得默认放权）。
    管理员恒有全部权限。
    """

    资料删除 = "material.delete"
    标签创建 = "tag.create"
    选题生成 = "topic.generate"
    选题手动新增 = "topic.create"
    选题修改 = "topic.update"
    脚本修改 = "script.update"
    脚本版本查看 = "script.version.view"
    脚本版本回退 = "script.version.rollback"
    数据录入导入 = "rawdata.input"
    分析任务执行 = "analysis.task.execute"
    分析结果审核 = "analysis.result.review"
    回写反哺 = "analysis.writeback"
    提示词配置 = "prompt.config"


ALL_PERMISSIONS: list[str] = [p.value for p in Permission]
