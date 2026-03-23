from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .blueprint import finalize_blueprint
from .llm import LLMBackend


def _normalize_metadata(
    *,
    book_title: str,
    authors: list[str] | None = None,
    edition: str | None = None,
    publisher: str | None = None,
    isbn: str | None = None,
) -> dict[str, Any]:
    return {
        "title": book_title.strip(),
        "authors": authors or [],
        "edition": edition or "",
        "publisher": publisher or "",
        "isbn": isbn or "",
    }


def _parse_toc_text(toc_text: str) -> list[dict[str, Any]]:
    chapters: list[dict[str, Any]] = []
    for index, raw_line in enumerate(toc_text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        match = re.match(r"^(第[0-9一二三四五六七八九十百]+章)\s*[·\-—:：]?\s*(.+)$", line)
        if match:
            prefix, title = match.groups()
            chapter_id = f"{prefix}·{title.strip()}"
            aliases = [chapter_id, title.strip(), line]
            chapter_title = title.strip()
        else:
            chapter_title = line
            chapter_id = line
            aliases = [line]
        chapters.append(
            {
                "chapter_id": chapter_id,
                "title": chapter_title,
                "aliases": aliases,
                "expected_topics": [],
            }
        )
    if not chapters:
        raise ValueError("TOC text did not contain any chapter lines.")
    return chapters


def _transcript_inventory(input_dir: Path) -> list[dict[str, Any]]:
    return [
        {
            "transcript_file": file.name,
            "transcript_stem": file.stem,
        }
        for file in sorted(input_dir.glob("*.md"))
    ]


def bootstrap_course_blueprint(
    *,
    input_dir: Path,
    book_title: str,
    toc_text: str | None,
    llm_backend: LLMBackend | None,
    authors: list[str] | None = None,
    edition: str | None = None,
    publisher: str | None = None,
    isbn: str | None = None,
) -> dict[str, Any]:
    metadata = _normalize_metadata(
        book_title=book_title,
        authors=authors,
        edition=edition,
        publisher=publisher,
        isbn=isbn,
    )
    transcript_inventory = _transcript_inventory(input_dir)

    if toc_text:
        blueprint = {
            "course_name": metadata["title"],
            "source_type": "published_textbook",
            "book": metadata,
            "chapters": _parse_toc_text(toc_text),
            "provenance": {
                "metadata": {"strategy": "user_input"},
                "chapter_structure": {"strategy": "user_toc"},
            },
        }
        return finalize_blueprint(blueprint)

    if llm_backend is not None:
        response = llm_backend.generate_json(
            agent_name="blueprint_builder",
            prompt=(
                "你是教材课程 blueprint builder。优先保守使用用户提供的教材标题与 transcript 清单，"
                "生成 course_name、chapters、provenance.chapter_structure.strategy。"
            ),
            payload={
                "book": metadata,
                "transcript_inventory": transcript_inventory,
                "source_type": "published_textbook",
            },
        )
        blueprint = {
            "course_name": response.get("course_name", metadata["title"]),
            "source_type": "published_textbook",
            "book": metadata,
            "chapters": response.get("chapters", []),
            "provenance": {
                "metadata": {"strategy": "user_input"},
                "chapter_structure": response.get("provenance", {}).get(
                    "chapter_structure",
                    {"strategy": "llm_completed"},
                ),
            },
        }
        return finalize_blueprint(blueprint)

    blueprint = {
        "course_name": metadata["title"],
        "source_type": "published_textbook",
        "book": metadata,
        "chapters": [
            {
                "chapter_id": item["transcript_stem"],
                "title": item["transcript_stem"],
                "aliases": [item["transcript_stem"]],
                "expected_topics": [],
            }
            for item in transcript_inventory
        ],
        "provenance": {
            "metadata": {"strategy": "user_input"},
            "chapter_structure": {"strategy": "transcript_inventory"},
        },
    }
    return finalize_blueprint(blueprint)


def load_toc_text(toc_file: Path | None, toc_text: str | None) -> str | None:
    if toc_text:
        return toc_text
    if toc_file and toc_file.exists():
        return toc_file.read_text(encoding="utf-8")
    return None


def describe_source(input_dir: Path) -> dict[str, Any]:
    inventory = _transcript_inventory(input_dir)
    return {
        "input_dir": str(input_dir),
        "transcript_count": len(inventory),
        "transcripts": inventory,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
