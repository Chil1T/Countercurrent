from __future__ import annotations

import json
import shutil
from pathlib import Path

from server.app.models.course_draft import CourseDraft, SubtitleAssetInput


class DuplicateSubtitleFilenameError(ValueError):
    pass


class DraftInputStorage:
    def __init__(self, output_root: Path) -> None:
        self._drafts_root = output_root / "_gui" / "drafts"

    def persist_subtitle_text(self, draft_id: str, subtitle_text: str) -> Path:
        input_dir = self.input_dir(draft_id)
        if input_dir.exists():
            shutil.rmtree(input_dir)
        input_dir.mkdir(parents=True, exist_ok=True)
        subtitle_path = input_dir / "chapter-01.md"
        subtitle_path.write_text(subtitle_text, encoding="utf-8")
        return subtitle_path

    def persist_subtitle_assets(self, draft_id: str, assets: list[SubtitleAssetInput]) -> list[Path]:
        input_dir = self.input_dir(draft_id)
        if input_dir.exists():
            shutil.rmtree(input_dir)
        input_dir.mkdir(parents=True, exist_ok=True)

        paths: list[Path] = []
        seen_filenames: set[str] = set()
        for index, asset in enumerate(assets, start=1):
            filename = Path(asset.filename.strip() or f"chapter-{index:02d}.md").name
            if not filename.endswith(".md"):
                filename = f"{filename}.md"
            normalized_key = filename.lower()
            if normalized_key in seen_filenames:
                raise DuplicateSubtitleFilenameError(f"Duplicate subtitle filename: {filename}")
            seen_filenames.add(normalized_key)
            target = input_dir / filename
            target.write_text(asset.content, encoding="utf-8")
            paths.append(target)
        return paths

    def persist_draft(self, draft: CourseDraft) -> Path:
        path = self.draft_path(draft.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(draft.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def load_draft(self, draft_id: str) -> CourseDraft | None:
        path = self.draft_path(draft_id)
        if not path.exists():
            return None
        return CourseDraft.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def input_dir(self, draft_id: str) -> Path:
        return self._drafts_root / draft_id / "input"

    def draft_path(self, draft_id: str) -> Path:
        return self._drafts_root / draft_id / "draft.json"

    def has_runtime_input(self, draft_id: str) -> bool:
        input_dir = self.input_dir(draft_id)
        return input_dir.exists() and any(input_dir.glob("*.md"))
