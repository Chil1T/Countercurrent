"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import {
  CourseDraft,
  createCourseDraft,
  getCourseDraft,
} from "@/lib/api/course-drafts";

const defaultSlots = [
  { kind: "subtitle", label: "字幕", supported: true, count: 0 },
  { kind: "audio_video", label: "音视频", supported: false, count: 0 },
  { kind: "courseware", label: "课件", supported: false, count: 0 },
  { kind: "textbook", label: "教材", supported: true, count: 0 },
];

export function CourseDraftWorkbench({
  initialDraftId,
}: {
  initialDraftId: string | null;
}) {
  const router = useRouter();
  const subtitleFileInputRef = useRef<HTMLInputElement | null>(null);
  const [bookTitle, setBookTitle] = useState("");
  const [uploadedSubtitleFiles, setUploadedSubtitleFiles] = useState<File[]>([]);
  const [subtitleAssets, setSubtitleAssets] = useState([
    { filename: "chapter-01.md", content: "" },
  ]);
  const [draft, setDraft] = useState<CourseDraft | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadDraft() {
      if (!initialDraftId) {
        if (!cancelled) {
          setDraft(null);
        }
        return;
      }

      try {
        const nextDraft = await getCourseDraft(initialDraftId);
        if (cancelled) {
          return;
        }
        setDraft(nextDraft);
        setBookTitle(nextDraft.book_title);
        setError(null);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unknown error");
        }
      }
    }

    void loadDraft();

    return () => {
      cancelled = true;
    };
  }, [initialDraftId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const preparedSubtitleAssets = subtitleAssets.filter((asset) => asset.content.trim().length > 0);
      const formData = new FormData();
      formData.append("book_title", bookTitle);
      for (const file of uploadedSubtitleFiles) {
        formData.append("subtitle_files", file, file.name);
      }
      for (const asset of preparedSubtitleAssets) {
        const blob = new Blob([asset.content], { type: "text/markdown" });
        formData.append("subtitle_files", blob, asset.filename);
      }

      const nextDraft =
        uploadedSubtitleFiles.length > 0 || preparedSubtitleAssets.length > 0
          ? await createCourseDraft(formData)
          : await createCourseDraft({
              book_title: bookTitle,
            });
      setDraft(nextDraft);
      router.replace(`/courses/new/input?draftId=${nextDraft.id}`);
    } catch (submitError) {
      setError(
        submitError instanceof Error ? submitError.message : "Unknown error",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  const slots = (draft?.input_slots ?? defaultSlots).filter((slot) => slot.kind !== "course_link");

  return (
    <section className="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_340px]">
      <form
        onSubmit={handleSubmit}
        className="min-w-0 rounded-[28px] border border-stone-200 bg-stone-50 p-5 xl:p-6"
      >
        <h3 className="text-xl font-semibold">素材输入分区</h3>
        <p className="mt-2 text-sm leading-7 text-stone-600">
          第一条可执行闭环现在接通了教材名和文件感知的字幕资产；其他模态分区继续保留占位。
        </p>

        <div className="mt-5 grid gap-4">
          <label className="rounded-2xl border border-stone-200 bg-white px-4 py-4">
            <div className="text-sm font-medium text-stone-700">教材名</div>
            <input
              value={bookTitle}
              onChange={(event) => setBookTitle(event.target.value)}
              required
              placeholder="例如：Database System Concepts"
              className="mt-3 w-full border-none bg-transparent text-sm text-stone-800 outline-none"
            />
          </label>

          <div className="rounded-2xl border border-stone-200 bg-white px-4 py-4">
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium text-stone-700">字幕资产</div>
              <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-medium uppercase tracking-[0.16em] text-emerald-700">
                Runtime Ready
              </span>
            </div>
            <div className="mt-4 rounded-2xl border border-dashed border-stone-300 bg-stone-50 px-4 py-4">
              <div className="text-sm font-medium text-stone-700">上传字幕文件</div>
              <button
                type="button"
                onClick={() => subtitleFileInputRef.current?.click()}
                className="mt-3 inline-flex cursor-pointer rounded-full bg-stone-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-stone-700"
              >
                选择文件
              </button>
              <input
                ref={subtitleFileInputRef}
                id="subtitle-files-input"
                type="file"
                multiple
                accept=".md,.txt,text/plain,text/markdown"
                onChange={(event) =>
                  setUploadedSubtitleFiles(Array.from(event.target.files ?? []))
                }
                className="sr-only"
              />
              <div className="mt-3 space-y-2 text-xs leading-6 text-stone-600">
                {uploadedSubtitleFiles.length > 0 ? (
                  uploadedSubtitleFiles.map((file) => (
                    <div key={`${file.name}-${file.size}`}>{file.name}</div>
                  ))
                ) : (
                  <div>未选择本地文件，仍可在下方手工录入字幕内容。</div>
                )}
              </div>
            </div>
            <div className="mt-4 space-y-4">
              {subtitleAssets.map((asset, index) => (
                <div
                  key={`${index}-${asset.filename}`}
                  className="rounded-2xl border border-stone-200 bg-stone-50 px-4 py-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <input
                      value={asset.filename}
                      onChange={(event) =>
                        setSubtitleAssets((current) =>
                          current.map((item, itemIndex) =>
                            itemIndex === index
                              ? { ...item, filename: event.target.value }
                              : item,
                          ),
                        )
                      }
                      placeholder="chapter-01.md"
                      className="w-full border-none bg-transparent text-sm font-medium text-stone-700 outline-none"
                    />
                    {subtitleAssets.length > 1 ? (
                      <button
                        type="button"
                        onClick={() =>
                          setSubtitleAssets((current) => current.filter((_, itemIndex) => itemIndex !== index))
                        }
                        className="text-xs font-medium uppercase tracking-[0.16em] text-stone-500 transition hover:text-stone-800"
                      >
                        Remove
                      </button>
                    ) : null}
                  </div>
                  <textarea
                    value={asset.content}
                    onChange={(event) =>
                      setSubtitleAssets((current) =>
                        current.map((item, itemIndex) =>
                          itemIndex === index
                            ? { ...item, content: event.target.value }
                            : item,
                        ),
                      )
                    }
                    placeholder={"# 第1章 绪论\n\n这里粘贴一段字幕或转录文本。"}
                    className="mt-3 min-h-32 w-full resize-y border-none bg-transparent text-sm leading-7 text-stone-800 outline-none"
                  />
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={() =>
                setSubtitleAssets((current) => [
                  ...current,
                  { filename: `chapter-${String(current.length + 1).padStart(2, "0")}.md`, content: "" },
                ])
              }
              className="mt-4 rounded-full border border-stone-300 px-4 py-2 text-xs font-medium uppercase tracking-[0.16em] text-stone-600 transition hover:bg-stone-100"
            >
              Add Transcript
            </button>
          </div>

          {slots.map((slot) => (
            <div
              key={slot.kind}
              className="rounded-2xl border border-dashed border-stone-300 bg-white px-4 py-5 text-sm text-stone-700"
            >
              <div className="flex items-center justify-between">
                <span>{slot.label}</span>
                <span
                  className={`rounded-full px-2 py-0.5 text-[11px] font-medium uppercase tracking-[0.16em] ${
                    slot.supported
                      ? "bg-emerald-100 text-emerald-700"
                      : "bg-stone-200 text-stone-600"
                  }`}
                >
                  {slot.supported ? `Ready · ${slot.count}` : "Coming soon"}
                </span>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-4">
          <button
            type="submit"
            disabled={isSubmitting}
            className="rounded-full bg-stone-900 px-5 py-3 text-sm font-medium text-white transition hover:bg-stone-700 disabled:cursor-not-allowed disabled:bg-stone-400"
          >
            {isSubmitting ? "识别中..." : "保存并识别课程信息"}
          </button>
          {draft ? (
            <span className="text-sm text-emerald-700">
              已生成草稿：{draft.id} / {draft.runtime_ready ? "可运行" : "待补输入"}
            </span>
          ) : null}
          {draft ? (
            <button
              type="button"
              onClick={() => router.push(`/courses/new/config?draftId=${draft.id}`)}
              className="rounded-full border border-stone-300 px-5 py-3 text-sm font-medium text-stone-700 transition hover:bg-stone-100"
            >
              前往配置页
            </button>
          ) : null}
        </div>

        {error ? (
          <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        ) : null}
      </form>

      <div className="xl:self-start xl:sticky xl:top-24">
        <div className="min-w-0 rounded-[28px] border border-stone-200 bg-white p-5 xl:p-6">
          <h3 className="text-xl font-semibold">课程识别摘要</h3>
          <ul className="mt-5 space-y-3 text-sm leading-7 text-stone-600">
            <li>草稿 ID：{draft?.id ?? "尚未生成"}</li>
            <li>课程 ID：{draft?.course_id ?? "待生成"}</li>
            <li>课程名：{draft?.detected.course_name ?? "待识别"}</li>
            <li>教材名：{draft?.detected.textbook_title ?? "待填写"}</li>
            <li>
              章节结构：
              {draft?.detected.chapter_count == null
                ? " 待生成"
                : ` ${draft.detected.chapter_count}`}
            </li>
            <li>
              素材完整度：
              {draft ? ` ${draft.detected.asset_completeness}%` : " 0%"}
            </li>
            <li>运行就绪：{draft?.runtime_ready ? "已就绪" : "未就绪"}</li>
          </ul>
        </div>
      </div>
    </section>
  );
}
