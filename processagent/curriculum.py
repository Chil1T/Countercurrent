from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChapterProfile:
    chapter_id: str
    canonical_title: str
    expected_topics: tuple[str, ...]
    cross_chapter_links: tuple[str, ...]
    interview_focus: tuple[str, ...]


DEFAULT_PROFILE = ChapterProfile(
    chapter_id="通用章节",
    canonical_title="数据库系统概论",
    expected_topics=(
        "核心概念",
        "关键术语",
        "典型比较",
        "面试常见追问",
    ),
    cross_chapter_links=("与前置章节的概念承接", "与后续章节的应用承接"),
    interview_focus=("定义", "区别", "使用场景"),
)


CHAPTER_PROFILES: dict[str, ChapterProfile] = {
    "第一章·绪论": ChapterProfile(
        chapter_id="第一章·绪论",
        canonical_title="数据库系统概述",
        expected_topics=(
            "数据库发展阶段",
            "数据模型",
            "三层模式两级映像",
            "数据库、DBMS、DBS、DBA 的区别",
        ),
        cross_chapter_links=("第二章关系模型", "第三章 SQL", "第七章数据库设计"),
        interview_focus=("术语区分", "数据独立性", "体系结构"),
    ),
    "第二章·关系数据库": ChapterProfile(
        chapter_id="第二章·关系数据库",
        canonical_title="关系模型与关系运算",
        expected_topics=("关系模型基本概念", "关系完整性", "关系代数", "关系演算"),
        cross_chapter_links=("第一章绪论", "第三章 SQL"),
        interview_focus=("关系模型优点", "关系代数操作", "键与完整性"),
    ),
    "第三章·关系数据库标准语言SQL": ChapterProfile(
        chapter_id="第三章·关系数据库标准语言SQL",
        canonical_title="SQL 语言总览",
        expected_topics=("DDL", "DML", "DCL", "视图与索引"),
        cross_chapter_links=("第二章关系模型", "第四章安全性", "第五章完整性"),
        interview_focus=("SQL 分类", "约束定义", "授权撤权"),
    ),
    "第三章·SQL语言-select查询": ChapterProfile(
        chapter_id="第三章·SQL语言-select查询",
        canonical_title="SQL 查询语句",
        expected_topics=("SELECT 结构", "WHERE 条件", "聚合与分组", "连接与排序"),
        cross_chapter_links=("第二章关系代数", "第三章 SQL 总览"),
        interview_focus=("查询语义", "易错点", "复杂查询追问"),
    ),
    "第四章·数据库安全性": ChapterProfile(
        chapter_id="第四章·数据库安全性",
        canonical_title="数据库安全性",
        expected_topics=("安全控制", "自主存取控制", "强制存取控制", "审计"),
        cross_chapter_links=("第三章 DCL", "第十二章并发控制"),
        interview_focus=("安全与完整性区别", "授权机制", "审计作用"),
    ),
    "第五章·数据库完整性": ChapterProfile(
        chapter_id="第五章·数据库完整性",
        canonical_title="数据库完整性",
        expected_topics=("实体完整性", "参照完整性", "用户定义完整性"),
        cross_chapter_links=("第二章关系模型", "第三章 SQL"),
        interview_focus=("三类完整性", "约束实现", "完整性与安全性区别"),
    ),
    "第六章·关系数据理论": ChapterProfile(
        chapter_id="第六章·关系数据理论",
        canonical_title="关系数据理论",
        expected_topics=("函数依赖", "候选码", "范式", "模式分解"),
        cross_chapter_links=("第二章关系模型", "第七章数据库设计"),
        interview_focus=("范式判断", "依赖分析", "无损连接"),
    ),
    "第六章·关系数据理论-范式判断与分解": ChapterProfile(
        chapter_id="第六章·关系数据理论-范式判断与分解",
        canonical_title="范式判断与分解",
        expected_topics=("范式判断", "保持函数依赖", "无损连接分解"),
        cross_chapter_links=("第六章关系数据理论", "第七章数据库设计"),
        interview_focus=("分解步骤", "判断依据", "常见误区"),
    ),
    "第七章·数据库设计": ChapterProfile(
        chapter_id="第七章·数据库设计",
        canonical_title="数据库设计",
        expected_topics=("需求分析", "概念结构设计", "逻辑结构设计", "物理结构设计"),
        cross_chapter_links=("第一章数据模型", "第六章关系数据理论"),
        interview_focus=("ER 图", "设计流程", "范式落地"),
    ),
    "第十一章·数据库恢复技术": ChapterProfile(
        chapter_id="第十一章·数据库恢复技术",
        canonical_title="数据库恢复技术",
        expected_topics=("事务故障", "系统故障", "介质故障", "日志与检查点"),
        cross_chapter_links=("第十二章并发控制", "事务管理"),
        interview_focus=("恢复策略", "日志作用", "故障分类"),
    ),
    "第十二章·并发控制": ChapterProfile(
        chapter_id="第十二章·并发控制",
        canonical_title="并发控制",
        expected_topics=("并发问题", "封锁协议", "死锁", "可串行化"),
        cross_chapter_links=("第十一章恢复技术", "事务管理"),
        interview_focus=("并发异常", "封锁粒度", "死锁处理"),
    ),
}


def get_chapter_profile(chapter_id: str) -> ChapterProfile:
    return CHAPTER_PROFILES.get(chapter_id, DEFAULT_PROFILE)
