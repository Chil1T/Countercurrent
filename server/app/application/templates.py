from __future__ import annotations

from server.app.models.template_preset import TemplatePreset


def default_template_presets() -> list[TemplatePreset]:
    return [
        TemplatePreset(
            id="standard-knowledge-pack",
            name="标准知识包",
            description="面向 NotebookLM 的平衡型默认模板。",
            expected_outputs=[
                "01-精讲.md",
                "02-术语与定义.md",
                "03-面试问答.md",
                "04-跨章关联.md",
                "05-疑点与待核.md",
            ],
        ),
        TemplatePreset(
            id="lecture-deep-dive",
            name="精讲优先",
            description="提高精讲与概念串联密度，适合讲义型课程。",
            expected_outputs=[
                "01-精讲.md",
                "04-跨章关联.md",
                "global_glossary.md",
            ],
        ),
        TemplatePreset(
            id="interview-focus",
            name="面试强化",
            description="提高问答、定义和 reviewer 检查权重。",
            expected_outputs=[
                "02-术语与定义.md",
                "03-面试问答.md",
                "interview_index.md",
            ],
        ),
    ]
