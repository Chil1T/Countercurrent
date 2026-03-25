from __future__ import annotations

import json
import re
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .blueprint import match_chapter_for_transcript, save_blueprint
from .bootstrap import bootstrap_course_blueprint
from .llm import LLMBackend

REQUIRED_PACK_FILES = (
    "01-精讲.md",
    "02-术语与定义.md",
    "03-面试问答.md",
    "04-跨章关联.md",
    "05-疑点与待核.md",
)
PACK_WRITER_FILES = {
    "write_lecture_note": "01-精讲.md",
    "write_terms": "02-术语与定义.md",
    "write_interview_qa": "03-面试问答.md",
    "write_cross_links": "04-跨章关联.md",
    "write_open_questions": "05-疑点与待核.md",
}
GLOBAL_WRITER_FILES = {
    "build_global_glossary": "global_glossary.md",
    "build_interview_index": "interview_index.md",
}
WRITER_STAGE_SETS = {
    "lecture_deep_dive": (
        "write_lecture_note",
        "write_terms",
        "write_cross_links",
    ),
    "standard_knowledge_pack": (
        "write_lecture_note",
        "write_terms",
        "write_interview_qa",
        "write_cross_links",
        "write_open_questions",
    ),
    "interview_knowledge_base": (
        "write_lecture_note",
        "write_terms",
        "write_interview_qa",
        "write_cross_links",
    ),
}
PIPELINE_SIGNATURE = "pipeline-v4"
HOSTED_PRESSURE_STAGES = (
    "curriculum_anchor",
    "gap_fill",
    "pack_plan",
    "write_lecture_note",
    "write_terms",
    "write_interview_qa",
    "write_cross_links",
    "write_open_questions",
    "review",
    "build_global_glossary",
    "build_interview_index",
)
EXECUTION_STRATEGY = {
    "chapter_loop": "serial",
    "writer_loop": "serial",
    "global_consolidation": "serial",
}


@dataclass
class PipelineConfig:
    input_dir: Path
    output_dir: Path
    model: str = ""
    clean_output: bool = False
    course_blueprint: dict[str, Any] | None = None
    stage_models: dict[str, str] = field(default_factory=dict)
    backend_name: str = "heuristic"
    enable_review: bool = False
    run_global_consolidation: bool = False


class IngestAgent:
    _filler_tokens = ("嗯", "啊", "呃", "然后呢", "就是说", "这个", "那个")

    def run(self, chapter_id: str, transcript_text: str) -> dict[str, Any]:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", transcript_text) if p.strip()]
        chunks: list[dict[str, Any]] = []
        chunk_buffer: list[str] = []
        raw_buffer: list[str] = []
        counter = 1

        for paragraph in paragraphs or [transcript_text]:
            for sentence in self._split_sentences(paragraph):
                raw_sentence = sentence.strip()
                if not raw_sentence:
                    continue
                raw_buffer.append(raw_sentence)
                chunk_buffer.append(raw_sentence)
                if len("".join(chunk_buffer)) >= 120 or len(chunk_buffer) >= 3:
                    chunks.append(self._make_chunk(counter, raw_buffer))
                    counter += 1
                    chunk_buffer = []
                    raw_buffer = []

        if raw_buffer:
            chunks.append(self._make_chunk(counter, raw_buffer))

        return {
            "chapter_id": chapter_id,
            "chunks": chunks,
        }

    def _split_sentences(self, text: str) -> list[str]:
        return [part for part in re.split(r"(?<=[。！？!?])", text) if part.strip()]

    def _make_chunk(self, counter: int, raw_sentences: list[str]) -> dict[str, Any]:
        raw_text = "".join(raw_sentences).strip()
        clean_text = raw_text
        noise_flags: list[str] = []
        for token in self._filler_tokens:
            if token in clean_text:
                noise_flags.append("filler")
                clean_text = clean_text.replace(token, "")
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        clean_text = re.sub(r"([，。！？])\1+", r"\1", clean_text)
        if "。。" in raw_text or "！！" in raw_text:
            noise_flags.append("repetition")
        return {
            "chunk_id": f"chunk-{counter:03d}",
            "raw_text": raw_text,
            "clean_text": clean_text,
            "speaker_role": "lecturer",
            "noise_flags": sorted(set(noise_flags)),
        }


@dataclass
class PipelineRunner:
    config: PipelineConfig
    llm_backend: LLMBackend | None = None

    def __post_init__(self) -> None:
        if self.llm_backend is None:
            self.llm_backend = HeuristicLLMBackend()
        self.prompt_dir = Path(__file__).with_name("prompts")
        self.ingest_agent = IngestAgent()
        self.course_blueprint = self.config.course_blueprint or bootstrap_course_blueprint(
            input_dir=self.config.input_dir,
            book_title=self.config.input_dir.name or "未命名课程",
            toc_text=None,
            llm_backend=None,
        )
        self.course_dir = self.config.output_dir / "courses" / self.course_blueprint["course_id"]
        self.runtime_state_path = self.course_dir / "runtime_state.json"
        self.blueprint_path = self.course_dir / "course_blueprint.json"
        self.llm_call_log_path = self.course_dir / "runtime" / "llm_calls.jsonl"
        self.runtime_state = self._load_runtime_state()

    def run(self) -> None:
        if self.config.clean_output and self.course_dir.exists():
            shutil.rmtree(self.course_dir)
            self.runtime_state = self._fresh_runtime_state()

        self.course_dir.mkdir(parents=True, exist_ok=True)
        save_blueprint(self.blueprint_path, self.course_blueprint)
        self._persist_runtime_state()

        if self.config.run_global_consolidation:
            self._run_global_consolidation()
            self._persist_runtime_state()
            return

        for transcript_file in sorted(self.config.input_dir.glob("*.md")):
            chapter_blueprint = match_chapter_for_transcript(self.course_blueprint, transcript_file.stem)
            chapter_output_id = chapter_blueprint["chapter_id"]
            chapter_dir = self.course_dir / "chapters" / chapter_output_id
            intermediate_dir = chapter_dir / "intermediate"
            notebooklm_dir = chapter_dir / "notebooklm"
            intermediate_dir.mkdir(parents=True, exist_ok=True)
            notebooklm_dir.mkdir(parents=True, exist_ok=True)
            chapter_changed = False

            normalized = self._load_step_json(
                chapter_id=chapter_output_id,
                step_name="ingest",
                path=intermediate_dir / "normalized_transcript.json",
                require_blueprint=False,
            )
            if normalized is None:
                normalized = self.ingest_agent.run(
                    chapter_id=chapter_output_id,
                    transcript_text=transcript_file.read_text(encoding="utf-8"),
                )
                self._write_json(intermediate_dir / "normalized_transcript.json", normalized)
                self._mark_step_complete(chapter_output_id, "ingest", require_blueprint=False)
                chapter_changed = True

            topic_map = self._load_step_json(
                chapter_id=chapter_output_id,
                step_name="curriculum_anchor",
                path=intermediate_dir / "topic_anchor_map.json",
            )
            if topic_map is None:
                topic_map = self._run_agent(
                    "curriculum_anchor",
                    {
                        "course_blueprint": self._slim_course_blueprint(),
                        "chapter_blueprint": chapter_blueprint,
                        "normalized_transcript": normalized,
                    },
                    scope=chapter_output_id,
                )
                self._write_json(intermediate_dir / "topic_anchor_map.json", topic_map)
                self._mark_step_complete(chapter_output_id, "curriculum_anchor")
                chapter_changed = True

            augmentation = self._load_step_json(
                chapter_id=chapter_output_id,
                step_name="gap_fill",
                path=intermediate_dir / "augmentation_candidates.json",
            )
            if augmentation is None:
                augmentation = self._run_agent(
                    "gap_fill",
                    {
                        "course_blueprint": self._slim_course_blueprint(),
                        "chapter_blueprint": chapter_blueprint,
                        "normalized_transcript": normalized,
                        "topic_anchor_map": topic_map,
                    },
                    scope=chapter_output_id,
                )
                self._write_json(intermediate_dir / "augmentation_candidates.json", augmentation)
                self._mark_step_complete(chapter_output_id, "gap_fill")
                chapter_changed = True

            pack_payload = self._build_pack_payload(
                chapter_blueprint=chapter_blueprint,
                normalized=normalized,
                topic_map=topic_map,
                augmentation=augmentation,
            )
            pack_plan_path = intermediate_dir / "pack_plan.json"
            pack_plan = None if chapter_changed else self._load_step_json(
                chapter_id=chapter_output_id,
                step_name="pack_plan",
                path=pack_plan_path,
            )
            if pack_plan is None:
                pack_plan = self._run_agent(
                    "pack_plan",
                    pack_payload,
                    scope=chapter_output_id,
                )
                self._write_json(pack_plan_path, pack_plan)
                self._mark_step_complete(chapter_output_id, "pack_plan")
                chapter_changed = True

            pack_files: dict[str, str] = {}
            for writer_name in self._active_writer_names():
                file_name = PACK_WRITER_FILES[writer_name]
                output_path = notebooklm_dir / file_name
                content = None if chapter_changed else self._load_step_text(
                    chapter_id=chapter_output_id,
                    step_name=writer_name,
                    path=output_path,
                )
                if content is None:
                    content = self._run_text_agent(
                        writer_name,
                        self._build_writer_payload(
                            chapter_blueprint=chapter_blueprint,
                            normalized=normalized,
                            topic_map=topic_map,
                            augmentation=augmentation,
                            pack_plan=pack_plan,
                        ),
                        scope=chapter_output_id,
                    )
                    output_path.write_text(content, encoding="utf-8")
                    self._mark_step_complete(chapter_output_id, writer_name)
                    chapter_changed = True
                pack_files[file_name] = content

            pack = {"files": pack_files}

            review_path = chapter_dir / "review_report.json"
            if self.config.enable_review:
                review = self._load_step_json(
                    chapter_id=chapter_output_id,
                    step_name="review",
                    path=review_path,
                ) if not chapter_changed else None
                if review is None:
                    review = self._run_agent(
                        "review",
                        self._build_review_payload(
                            chapter_blueprint=chapter_blueprint,
                            normalized=normalized,
                            topic_map=topic_map,
                            augmentation=augmentation,
                            pack=pack,
                        ),
                        scope=chapter_output_id,
                    )
                    self._write_json(review_path, review)
                    self._mark_step_complete(chapter_output_id, "review")
                    chapter_changed = True
            else:
                if review_path.exists():
                    review_path.unlink()
                self._clear_step_record(chapter_output_id, "review")

        self._persist_runtime_state()

    def _run_global_consolidation(self) -> None:
        active_chapters = self._collect_active_chapters()
        if not active_chapters:
            return

        global_dir = self.course_dir / "global"
        global_dir.mkdir(parents=True, exist_ok=True)
        global_payload = {
            "course_blueprint": self._slim_course_blueprint(),
            "chapters": active_chapters,
        }

        glossary = self._run_text_agent("build_global_glossary", global_payload, scope="global")
        (global_dir / "global_glossary.md").write_text(glossary, encoding="utf-8")
        self._mark_step_complete("global", "build_global_glossary")

        interview_index = self._run_text_agent("build_interview_index", global_payload, scope="global")
        (global_dir / "interview_index.md").write_text(interview_index, encoding="utf-8")
        self._mark_step_complete("global", "build_interview_index")

    def _collect_active_chapters(self) -> list[dict[str, Any]]:
        active_chapters: list[dict[str, Any]] = []
        chapters_dir = self.course_dir / "chapters"
        if not chapters_dir.exists():
            return active_chapters

        for chapter_blueprint in self.course_blueprint.get("chapters", []):
            chapter_id = chapter_blueprint["chapter_id"]
            notebooklm_dir = chapters_dir / chapter_id / "notebooklm"
            term_path = notebooklm_dir / "02-术语与定义.md"
            interview_path = notebooklm_dir / "03-面试问答.md"
            link_path = notebooklm_dir / "04-跨章关联.md"
            if not (term_path.exists() and link_path.exists()):
                continue
            active_chapters.append(
                {
                    "chapter_id": chapter_id,
                    "chapter_blueprint": chapter_blueprint,
                    "term_file": term_path.read_text(encoding="utf-8"),
                    "interview_file": interview_path.read_text(encoding="utf-8") if interview_path.exists() else "",
                    "link_file": link_path.read_text(encoding="utf-8"),
                }
            )
        return active_chapters

    def _slim_course_blueprint(self) -> dict[str, Any]:
        return {
            "course_id": self.course_blueprint["course_id"],
            "course_name": self.course_blueprint["course_name"],
            "source_type": self.course_blueprint["source_type"],
            "book": self.course_blueprint["book"],
            "policy": self.course_blueprint["policy"],
            "blueprint_hash": self.course_blueprint["blueprint_hash"],
        }

    def _run_agent(self, agent_name: str, payload: dict[str, Any], *, scope: str) -> dict[str, Any]:
        prompt = self._load_prompt(agent_name)
        model_override = self._resolve_stage_model(agent_name)
        started_at = time.perf_counter()
        response: dict[str, Any] | None = None
        error: Exception | None = None
        try:
            response = self.llm_backend.generate_json(
                agent_name=agent_name,
                prompt=prompt,
                payload=payload,
                model_override=model_override,
            )
            return response
        except Exception as exc:
            error = exc
            raise
        finally:
            self._record_llm_call(
                scope=scope,
                stage=agent_name,
                prompt=prompt,
                payload=payload,
                response=response,
                response_type="json",
                model_override=model_override,
                started_at=started_at,
                error=error,
            )

    def _run_text_agent(self, agent_name: str, payload: dict[str, Any], *, scope: str) -> str:
        prompt = self._load_prompt(agent_name)
        model_override = self._resolve_stage_model(agent_name)
        response: str | None = None
        error: Exception | None = None
        started_at = time.perf_counter()
        try:
            response = self.llm_backend.generate_text(
                agent_name=agent_name,
                prompt=prompt,
                payload=payload,
                model_override=model_override,
            )
            return response
        except Exception as exc:
            error = exc
            raise
        finally:
            self._record_llm_call(
                scope=scope,
                stage=agent_name,
                prompt=prompt,
                payload=payload,
                response=response,
                response_type="text",
                model_override=model_override,
                started_at=started_at,
                error=error,
            )

    def _load_prompt(self, agent_name: str) -> str:
        prompt_path = self.prompt_dir / f"{agent_name}.md"
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        return ""

    def _build_pack_payload(
        self,
        chapter_blueprint: dict[str, Any],
        normalized: dict[str, Any],
        topic_map: dict[str, Any],
        augmentation: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "course_blueprint": self._slim_course_blueprint(),
            "chapter_blueprint": chapter_blueprint,
            "transcript_evidence": self._slim_transcript(normalized),
            "topic_anchor_map": topic_map,
            "augmentation_digest": self._slim_augmentation(augmentation),
            "writer_profile": self._resolve_writer_profile(),
        }

    def _build_writer_payload(
        self,
        chapter_blueprint: dict[str, Any],
        normalized: dict[str, Any],
        topic_map: dict[str, Any],
        augmentation: dict[str, Any],
        pack_plan: dict[str, Any],
    ) -> dict[str, Any]:
        payload = self._build_pack_payload(
            chapter_blueprint=chapter_blueprint,
            normalized=normalized,
            topic_map=topic_map,
            augmentation=augmentation,
        )
        payload.pop("transcript_evidence", None)
        payload["evidence_summary"] = self._build_writer_evidence_summary(normalized, topic_map)
        payload["pack_plan"] = pack_plan
        return payload

    def _build_writer_evidence_summary(self, normalized: dict[str, Any], topic_map: dict[str, Any]) -> dict[str, Any]:
        highlights = [
            {
                "chunk_id": chunk["chunk_id"],
                "excerpt": chunk["clean_text"][:240],
                "speaker_role": chunk["speaker_role"],
            }
            for chunk in normalized["chunks"][:6]
        ]
        return {
            "chapter_summary": topic_map.get("chapter_summary", ""),
            "highlight_count": len(highlights),
            "highlights": highlights,
        }

    def _build_review_payload(
        self,
        chapter_blueprint: dict[str, Any],
        normalized: dict[str, Any],
        topic_map: dict[str, Any],
        augmentation: dict[str, Any],
        pack: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "course_blueprint": self._slim_course_blueprint(),
            "chapter_blueprint": chapter_blueprint,
            "transcript_evidence": self._slim_transcript(normalized),
            "topic_anchor_map": topic_map,
            "augmentation_digest": self._slim_augmentation(augmentation),
            "knowledge_pack": pack,
        }

    def _slim_transcript(self, normalized: dict[str, Any]) -> dict[str, Any]:
        return {
            "chapter_id": normalized["chapter_id"],
            "chunks": [
                {
                    "chunk_id": chunk["chunk_id"],
                    "clean_text": chunk["clean_text"],
                    "speaker_role": chunk["speaker_role"],
                    "noise_flags": chunk["noise_flags"],
                }
                for chunk in normalized["chunks"]
            ],
        }

    def _slim_augmentation(self, augmentation: dict[str, Any]) -> dict[str, Any]:
        candidates = augmentation.get("candidates", [])
        return {
            "candidate_count": len(candidates),
            "candidates": [
                {
                    "claim": item["claim"],
                    "source_type": item["source_type"],
                    "confidence": item["confidence"],
                    "support": item["support"][:240],
                    "allowed_in_final": item["allowed_in_final"],
                }
                for item in candidates
            ],
        }

    def _should_run_review(self, augmentation: dict[str, Any], pack: dict[str, Any]) -> bool:
        review_mode = self.course_blueprint.get("policy", {}).get("review_mode", "light")
        if review_mode != "light":
            return True
        candidates = augmentation.get("candidates", [])
        if any(item.get("source_type") == "inference" for item in candidates):
            return True
        if any(item.get("confidence") == "low" for item in candidates):
            return True
        non_transcript = [item for item in candidates if item.get("source_type") != "transcript"]
        if len(non_transcript) >= 3:
            return True
        return not all(name in pack.get("files", {}) for name in REQUIRED_PACK_FILES)

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _write_pack(self, notebooklm_dir: Path, pack: dict[str, Any]) -> None:
        files = pack.get("files", {})
        missing = [name for name in REQUIRED_PACK_FILES if name not in files]
        if missing:
            raise ValueError(f"Knowledge pack is missing required files: {', '.join(missing)}")
        for name, content in files.items():
            (notebooklm_dir / name).write_text(content, encoding="utf-8")

    def _load_step_json(
        self,
        *,
        chapter_id: str,
        step_name: str,
        path: Path,
        require_blueprint: bool = True,
    ) -> dict[str, Any] | None:
        if not self._step_is_valid(
            scope=chapter_id,
            step_name=step_name,
            required_paths=(path,),
            require_blueprint=require_blueprint,
        ):
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _load_step_text(
        self,
        *,
        chapter_id: str,
        step_name: str,
        path: Path,
        require_blueprint: bool = True,
    ) -> str | None:
        if not self._step_is_valid(
            scope=chapter_id,
            step_name=step_name,
            required_paths=(path,),
            require_blueprint=require_blueprint,
        ):
            return None
        return path.read_text(encoding="utf-8")

    def _load_step_pack(self, *, chapter_id: str, step_name: str, notebooklm_dir: Path) -> dict[str, Any] | None:
        required_paths = tuple(notebooklm_dir / name for name in REQUIRED_PACK_FILES)
        if not self._step_is_valid(
            scope=chapter_id,
            step_name=step_name,
            required_paths=required_paths,
            require_blueprint=True,
        ):
            return None
        files = {name: (notebooklm_dir / name).read_text(encoding="utf-8") for name in REQUIRED_PACK_FILES}
        return {"files": files}

    def _step_is_valid(
        self,
        *,
        scope: str,
        step_name: str,
        required_paths: tuple[Path, ...],
        require_blueprint: bool,
    ) -> bool:
        record = self._get_step_record(scope, step_name)
        if record is None:
            return False
        if not all(path.exists() for path in required_paths):
            return False
        if record.get("pipeline_signature") != PIPELINE_SIGNATURE:
            return False
        if require_blueprint and record.get("blueprint_hash") != self.course_blueprint["blueprint_hash"]:
            return False
        return record.get("status") == "completed"

    def _get_step_record(self, scope: str, step_name: str) -> dict[str, Any] | None:
        if scope == "global":
            return self.runtime_state.get("global", {}).get(step_name)
        return self.runtime_state.get("chapters", {}).get(scope, {}).get("steps", {}).get(step_name)

    def _clear_step_record(self, scope: str, step_name: str) -> None:
        if scope == "global":
            self.runtime_state.get("global", {}).pop(step_name, None)
        else:
            chapter_state = self.runtime_state.get("chapters", {}).get(scope, {})
            chapter_state.get("steps", {}).pop(step_name, None)
        self._persist_runtime_state()

    def _mark_step_complete(self, scope: str, step_name: str, require_blueprint: bool = True) -> None:
        payload = {
            "status": "completed",
            "updated_at": self._now_iso(),
            "blueprint_hash": self.course_blueprint["blueprint_hash"] if require_blueprint else None,
            "pipeline_signature": PIPELINE_SIGNATURE,
        }
        if scope == "global":
            self.runtime_state.setdefault("global", {})[step_name] = payload
        else:
            chapter_state = self.runtime_state.setdefault("chapters", {}).setdefault(scope, {"steps": {}})
            chapter_state.setdefault("steps", {})[step_name] = payload
        self.runtime_state["last_error"] = None
        self._persist_runtime_state()

    def _current_run_identity(self) -> dict[str, Any]:
        return {
            "review_enabled": self.config.enable_review,
            "review_mode": self.course_blueprint.get("policy", {}).get("review_mode"),
            "target_output": self.course_blueprint.get("policy", {}).get("target_output"),
        }

    def _load_runtime_state(self) -> dict[str, Any]:
        if not self.runtime_state_path.exists():
            return self._fresh_runtime_state()
        state = json.loads(self.runtime_state_path.read_text(encoding="utf-8"))
        run_identity = state.setdefault("run_identity", self._current_run_identity())
        state["course_id"] = self.course_blueprint["course_id"]
        state["blueprint_hash"] = self.course_blueprint["blueprint_hash"]
        state["provider"] = self.config.backend_name
        state["default_model"] = self.config.model
        state["stage_models"] = self.config.stage_models
        state["pipeline_signature"] = PIPELINE_SIGNATURE
        state["review_enabled"] = run_identity.get("review_enabled", self.config.enable_review)
        state["review_mode"] = run_identity.get("review_mode", self.course_blueprint.get("policy", {}).get("review_mode"))
        state["target_output"] = run_identity.get("target_output", self.course_blueprint.get("policy", {}).get("target_output"))
        state.setdefault("chapters", {})
        state.setdefault("global", {})
        state.setdefault("last_error", None)
        return state

    def _fresh_runtime_state(self) -> dict[str, Any]:
        run_identity = self._current_run_identity()
        return {
            "course_id": self.course_blueprint["course_id"],
            "blueprint_hash": self.course_blueprint["blueprint_hash"],
            "provider": self.config.backend_name,
            "default_model": self.config.model,
            "stage_models": self.config.stage_models,
            "pipeline_signature": PIPELINE_SIGNATURE,
            "review_enabled": run_identity["review_enabled"],
            "review_mode": run_identity["review_mode"],
            "target_output": run_identity["target_output"],
            "run_identity": run_identity,
            "chapters": {},
            "global": {},
            "last_error": None,
        }

    def _persist_runtime_state(self) -> None:
        self.runtime_state_path.parent.mkdir(parents=True, exist_ok=True)
        self.runtime_state_path.write_text(
            json.dumps(self.runtime_state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _record_llm_call(
        self,
        *,
        scope: str,
        stage: str,
        prompt: str,
        payload: dict[str, Any],
        response: dict[str, Any] | str | None,
        response_type: str,
        model_override: str | None,
        started_at: float,
        error: Exception | None,
    ) -> None:
        metadata = None
        consume = getattr(self.llm_backend, "consume_last_call_metadata", None)
        if callable(consume):
            metadata = consume()

        duration_ms = int((time.perf_counter() - started_at) * 1000)
        provider = self.config.backend_name
        model = model_override or self.config.model or None
        input_tokens = self._estimate_token_count(f"{prompt}\n{json.dumps(payload, ensure_ascii=False)}")
        output_tokens = self._estimate_token_count(response) if response is not None else None
        status = "error" if error else "completed"
        error_text = str(error) if error else None

        if metadata:
            provider = metadata.get("provider") or provider
            model = metadata.get("model") or model
            input_tokens = metadata.get("input_tokens") or input_tokens
            output_tokens = metadata.get("output_tokens") or output_tokens
            duration_ms = metadata.get("duration_ms") or duration_ms
            status = metadata.get("status") or status
            error_text = metadata.get("error") or error_text

        entry = {
            "course_id": self.course_blueprint["course_id"],
            "scope": scope,
            "stage": stage,
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "duration_ms": duration_ms,
            "status": status,
            "error": error_text,
            "response_type": response_type,
            "logged_at": self._now_iso(),
            "pipeline_signature": PIPELINE_SIGNATURE,
        }
        self.llm_call_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.llm_call_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _estimate_token_count(self, value: dict[str, Any] | str) -> int:
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        return max(1, len(text.encode("utf-8")) // 4)

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _resolve_stage_model(self, agent_name: str) -> str | None:
        return self.config.stage_models.get(agent_name)

    def _resolve_writer_profile(self) -> str:
        return self.course_blueprint.get("policy", {}).get("target_output", "interview_knowledge_base")

    def _active_writer_names(self) -> tuple[str, ...]:
        profile = self._resolve_writer_profile()
        return WRITER_STAGE_SETS.get(profile, WRITER_STAGE_SETS["standard_knowledge_pack"])


class HeuristicLLMBackend:
    def __init__(self) -> None:
        self._last_call_metadata: dict[str, Any] | None = None

    def generate_json(
        self,
        agent_name: str,
        prompt: str,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> dict[str, Any]:
        if agent_name == "blueprint_builder":
            response = self._blueprint_builder(payload)
        elif agent_name == "curriculum_anchor":
            response = self._curriculum_anchor(payload)
        elif agent_name == "gap_fill":
            response = self._gap_fill(payload)
        elif agent_name == "pack_plan":
            response = self._pack_plan(payload)
        elif agent_name == "compose_pack":
            response = self._compose_pack(payload)
        elif agent_name == "review":
            response = self._review(payload)
        elif agent_name == "canonicalize":
            response = self._canonicalize(payload)
        else:
            raise KeyError(f"Unsupported agent: {agent_name}")
        self._remember_call(payload, response, model_override)
        return response

    def generate_text(
        self,
        agent_name: str,
        prompt: str,
        payload: dict[str, Any],
        model_override: str | None = None,
    ) -> str:
        compose_pack = self._compose_pack(payload)
        if agent_name in PACK_WRITER_FILES:
            response = compose_pack["files"][PACK_WRITER_FILES[agent_name]]
            self._remember_call(payload, response, model_override)
            return response

        canonicalized = self._canonicalize(payload)
        if agent_name == "build_global_glossary":
            response = canonicalized["global_glossary"]
            self._remember_call(payload, response, model_override)
            return response
        if agent_name == "build_interview_index":
            response = canonicalized["interview_index"]
            self._remember_call(payload, response, model_override)
            return response
        raise KeyError(f"Unsupported text agent: {agent_name}")

    def consume_last_call_metadata(self) -> dict[str, Any] | None:
        metadata = self._last_call_metadata
        self._last_call_metadata = None
        return metadata

    def _remember_call(self, payload: dict[str, Any], response: dict[str, Any] | str, model_override: str | None) -> None:
        self._last_call_metadata = {
            "provider": "heuristic",
            "model": model_override,
            "input_tokens": max(1, len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) // 4),
            "output_tokens": max(
                1,
                len((response if isinstance(response, str) else json.dumps(response, ensure_ascii=False)).encode("utf-8"))
                // 4,
            ),
            "duration_ms": 0,
            "status": "completed",
            "error": None,
        }

    def _blueprint_builder(self, payload: dict[str, Any]) -> dict[str, Any]:
        chapters = [
            {
                "chapter_id": item["transcript_stem"],
                "title": item["transcript_stem"],
                "aliases": [item["transcript_stem"]],
                "expected_topics": [],
            }
            for item in payload.get("transcript_inventory", [])
        ]
        return {
            "course_name": payload["book"]["title"],
            "chapters": chapters,
            "provenance": {
                "chapter_structure": {
                    "strategy": "llm_completed",
                }
            },
        }

    def _curriculum_anchor(self, payload: dict[str, Any]) -> dict[str, Any]:
        chapter = payload["chapter_blueprint"]
        chunks = payload["normalized_transcript"]["chunks"]
        anchors = []
        for topic in chapter.get("expected_topics", []):
            supporting = [
                chunk["chunk_id"]
                for chunk in chunks
                if any(token and token in chunk["clean_text"] for token in self._topic_tokens(topic))
            ]
            anchors.append(
                {
                    "canonical_topic": topic,
                    "coverage_status": "covered" if supporting else "missing",
                    "supporting_chunk_ids": supporting,
                    "missing_expected_points": [] if supporting else [f"录音中未明确覆盖：{topic}"],
                }
            )
        return {
            "chapter_summary": f"{chapter.get('title', chapter['chapter_id'])} 的教材主题映射",
            "anchors": anchors,
        }

    def _gap_fill(self, payload: dict[str, Any]) -> dict[str, Any]:
        anchors = payload["topic_anchor_map"].get("anchors", [])
        candidates = []
        for anchor in anchors:
            if anchor["coverage_status"] != "covered":
                candidates.append(
                    {
                        "claim": f"{anchor['canonical_topic']} 应补充教材级定义、最小例子和章节衔接。",
                        "source_type": "textbook_prior",
                        "confidence": "medium",
                        "support": "教材常识补全",
                        "allowed_in_final": True,
                    }
                )
        return {"candidates": candidates}

    def _pack_plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        writer_profile = payload.get("writer_profile") or payload.get("course_blueprint", {}).get("policy", {}).get(
            "target_output",
            "interview_knowledge_base",
        )
        title = payload["chapter_blueprint"].get("title", payload["chapter_blueprint"]["chapter_id"])
        return {
            "writer_profile": writer_profile,
            "chapter_title": title,
            "files": [
                {"stage": "write_lecture_note", "file_name": "01-精讲.md", "goal": "基于 transcript 整理章节主线。"},
                {"stage": "write_terms", "file_name": "02-术语与定义.md", "goal": "提炼术语和保守定义。"},
                {"stage": "write_interview_qa", "file_name": "03-面试问答.md", "goal": "生成可检索的面试问答。"},
                {"stage": "write_cross_links", "file_name": "04-跨章关联.md", "goal": "解释章节前后依赖。"},
                {"stage": "write_open_questions", "file_name": "05-疑点与待核.md", "goal": "保留待核查与低置信度点。"},
            ],
        }

    def _build_writer_evidence_summary(self, normalized: dict[str, Any], topic_map: dict[str, Any]) -> dict[str, Any]:
        highlights = [
            {
                "chunk_id": chunk["chunk_id"],
                "excerpt": chunk["clean_text"][:240],
                "speaker_role": chunk["speaker_role"],
            }
            for chunk in normalized["chunks"][:6]
        ]
        return {
            "chapter_summary": topic_map.get("chapter_summary", ""),
            "highlight_count": len(highlights),
            "highlights": highlights,
        }

    def _compose_pack(self, payload: dict[str, Any]) -> dict[str, Any]:
        chapter = payload["chapter_blueprint"]
        transcript = payload.get("transcript_evidence")
        evidence_summary = payload.get("evidence_summary", {})
        anchors = payload["topic_anchor_map"].get("anchors", [])
        augmentation = payload["augmentation_digest"]
        candidates = augmentation.get("candidates", [])
        target_output = payload.get("course_blueprint", {}).get("policy", {}).get("target_output", "interview_knowledge_base")

        transcript_chunks = transcript.get("chunks", []) if transcript else []
        if transcript_chunks:
            lecture_lines = "\n".join(
                f"- `{chunk['chunk_id']}` {chunk['clean_text']}（来源：transcript）"
                for chunk in transcript_chunks
            )
        else:
            lecture_lines = "\n".join(
                f"- `{item['chunk_id']}` {item['excerpt']}（来源：证据摘要）"
                for item in evidence_summary.get("highlights", [])
            )
        lecture_lines = lecture_lines or "- 暂无 transcript 证据。"
        term_lines = "\n".join(
            f"- **{anchor['canonical_topic']}**："
            f"{'录音已覆盖。' if anchor['coverage_status'] == 'covered' else '录音未讲清，需教材补全。'}"
            for anchor in anchors
        ) or "- 本章术语待补充。"
        augment_lines = "\n".join(
            f"- {candidate['claim']}（来源：{candidate['source_type']}，置信度：{candidate['confidence']}）"
            for candidate in candidates
        ) or "- 暂无新增补全。"

        interview_focus = chapter.get("expected_topics") or [chapter.get("title", chapter["chapter_id"])]
        interview_lines = "\n".join(
            f"### {focus}\n- 结合本章内容解释“{focus}”的含义与应用。"
            for focus in interview_focus[:4]
        )
        link_lines = "\n".join(f"- {item}" for item in self._build_link_lines(payload["course_blueprint"], chapter))

        title = chapter.get("title", chapter["chapter_id"])
        lecture_heading = "## 录音证据"
        lecture_footer = "## 教材级补全"
        interview_heading = "## 概念题"
        interview_tail = ""
        if target_output == "lecture_deep_dive":
            lecture_heading = "## 课堂精讲主线"
            lecture_footer = "## 讲义化补充"
            interview_heading = "## 课堂复盘提问"
            interview_tail = "\n\n> 当前模板偏向课堂精讲，不强调面试口语化表达。"
        elif target_output == "standard_knowledge_pack":
            lecture_heading = "## 核心内容"
            lecture_footer = "## 标准补充"
            interview_heading = "## 自测问答"
            interview_tail = "\n\n> 当前模板采用平衡型知识包组织方式。"
        else:
            interview_tail = "\n\n> 当前模板强调面试表达与高频定义复述。"
        return {
            "files": {
                "01-精讲.md": f"# {title}·精讲\n\n{lecture_heading}\n{lecture_lines}\n\n{lecture_footer}\n{augment_lines}\n",
                "02-术语与定义.md": f"# {title}·术语与定义\n\n## 核心术语\n{term_lines}\n",
                "03-面试问答.md": f"# {title}·面试问答\n\n{interview_heading}\n{interview_lines}{interview_tail}\n",
                "04-跨章关联.md": f"# {title}·跨章关联\n\n## 前后章节承接\n{link_lines}\n",
                "05-疑点与待核.md": f"# {title}·疑点与待核\n\n## 待核查点\n{augment_lines}\n",
            }
        }

    def _review(self, payload: dict[str, Any]) -> dict[str, Any]:
        candidates = payload["augmentation_digest"].get("candidates", [])
        high_risk = [item for item in candidates if item.get("confidence") == "low" and item.get("allowed_in_final")]
        if high_risk:
            return {
                "status": "needs_attention",
                "issues": [
                    {
                        "severity": "high",
                        "issue_type": "low_confidence_claim",
                        "location": "05-疑点与待核.md",
                        "fix_hint": "降低低置信度补全的最终可见性，或补充 transcript 支撑。",
                    }
                ],
            }
        return {"status": "approved", "issues": []}

    def _canonicalize(self, payload: dict[str, Any]) -> dict[str, Any]:
        glossary_sections = ["# 全书术语表"]
        interview_sections = ["# 面试索引"]
        for chapter in payload.get("chapters", []):
            glossary_sections.append(f"\n## {chapter['chapter_id']}\n{chapter['term_file']}")
            interview_sections.append(f"\n## {chapter['chapter_id']}\n{chapter['interview_file']}")
        return {
            "global_glossary": "\n".join(glossary_sections).strip() + "\n",
            "interview_index": "\n".join(interview_sections).strip() + "\n",
        }

    def _build_link_lines(self, course_blueprint: dict[str, Any], chapter: dict[str, Any]) -> list[str]:
        titles = [item.get("title", item["chapter_id"]) for item in course_blueprint.get("chapters", [])]
        current = chapter.get("title", chapter["chapter_id"])
        if current not in titles:
            return ["与课程其他章节的概念承接待补。"]
        index = titles.index(current)
        lines = []
        if index > 0:
            lines.append(f"与上一章《{titles[index - 1]}》形成前置承接。")
        if index + 1 < len(titles):
            lines.append(f"为下一章《{titles[index + 1]}》提供概念基础。")
        return lines or ["本章为课程导入或收束章节。"]

    def _topic_tokens(self, topic: str) -> list[str]:
        return [token for token in re.split(r"[、·\s/]+", topic) if token]
