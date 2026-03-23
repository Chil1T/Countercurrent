# `course_blueprint.json` Schema

## Minimum Fields

```json
{
  "course_id": "数据库系统概论-xxxxxxxx",
  "course_name": "数据库系统概论",
  "source_type": "published_textbook",
  "book": {
    "title": "数据库系统概论",
    "authors": ["王珊", "萨师煊"],
    "edition": "第5版",
    "publisher": "高等教育出版社",
    "isbn": ""
  },
  "chapters": [
    {
      "chapter_id": "第一章·绪论",
      "title": "绪论",
      "aliases": ["第一章·绪论"],
      "expected_topics": []
    }
  ],
  "policy": {
    "augmentation_mode": "conservative",
    "review_mode": "light",
    "target_output": "interview_knowledge_base"
  },
  "provenance": {
    "metadata": {"strategy": "user_input"},
    "chapter_structure": {"strategy": "user_toc"}
  },
  "blueprint_hash": "..."
}
```

## Notes

- `source_type` 的 v1 固定为 `published_textbook`
- `chapter_id` 同时用作 runtime 目录名
- `blueprint_hash` 用于 checkpoint 兼容性判断
