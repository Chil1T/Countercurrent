from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any


def build_course_id(book_title: str) -> str:
    normalized = re.sub(r"\s+", "-", book_title.strip().lower())
    normalized = re.sub(r"[^0-9a-zA-Z\-\u4e00-\u9fff]+", "-", normalized).strip("-")
    if normalized:
        digest = hashlib.sha1(book_title.encode("utf-8")).hexdigest()[:8]
        return f"{normalized}-{digest}"
    return f"course-{hashlib.sha1(book_title.encode('utf-8')).hexdigest()[:8]}"


def build_blueprint_hash(blueprint: dict[str, Any]) -> str:
    payload = deepcopy(blueprint)
    payload.pop("blueprint_hash", None)
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def finalize_blueprint(blueprint: dict[str, Any]) -> dict[str, Any]:
    materialized = deepcopy(blueprint)
    materialized.setdefault("course_name", materialized["book"]["title"])
    materialized.setdefault("source_type", "published_textbook")
    materialized.setdefault("course_id", build_course_id(materialized["course_name"]))
    materialized.setdefault(
        "policy",
        {
            "augmentation_mode": "conservative",
            "review_mode": "light",
            "target_output": "interview_knowledge_base",
        },
    )
    materialized.setdefault(
        "provenance",
        {
            "metadata": {"strategy": "user_input"},
            "chapter_structure": {"strategy": "transcript_inventory"},
        },
    )
    for index, chapter in enumerate(materialized.get("chapters", []), start=1):
        chapter.setdefault("chapter_id", chapter.get("title") or f"chapter-{index:02d}")
        chapter.setdefault("aliases", [])
        chapter.setdefault("expected_topics", [])
    materialized["blueprint_hash"] = build_blueprint_hash(materialized)
    return materialized


def apply_policy_overrides(
    blueprint: dict[str, Any],
    *,
    review_mode: str | None = None,
    target_output: str | None = None,
) -> dict[str, Any]:
    materialized = deepcopy(blueprint)
    policy = deepcopy(materialized.get("policy", {}))
    if review_mode:
        policy["review_mode"] = review_mode
    if target_output:
        policy["target_output"] = target_output
    materialized["policy"] = policy
    materialized["blueprint_hash"] = build_blueprint_hash(materialized)
    return materialized


def load_blueprint(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_blueprint(path: Path, blueprint: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(blueprint, ensure_ascii=False, indent=2), encoding="utf-8")


def match_chapter_for_transcript(blueprint: dict[str, Any], transcript_stem: str) -> dict[str, Any]:
    for chapter in blueprint.get("chapters", []):
        aliases = {chapter.get("chapter_id", ""), chapter.get("title", ""), *chapter.get("aliases", [])}
        if transcript_stem in aliases:
            return chapter
        if chapter.get("title") and chapter["title"] in transcript_stem:
            return chapter
        if any(alias and alias in transcript_stem for alias in chapter.get("aliases", [])):
            return chapter
    return {
        "chapter_id": transcript_stem,
        "title": transcript_stem,
        "aliases": [transcript_stem],
        "expected_topics": [],
    }
