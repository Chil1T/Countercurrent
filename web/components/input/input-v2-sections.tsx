"use client";

import { ChangeEvent, FormEvent, RefObject } from "react";

import { CourseDraft, InputSlot } from "@/lib/api/course-drafts";
import { SurfaceCard } from "@/components/stitch-v2/surface-card";
import { StatusChip } from "@/components/stitch-v2/status-chip";

export type SubtitleAssetDraft = {
  filename: string;
  content: string;
};

export function InputV2Sections({
  bookTitle,
  uploadedSubtitleFiles,
  subtitleAssets,
  draft,
  slots,
  isSubmitting,
  error,
  onSubmit,
  onBookTitleChange,
  onOpenSubtitlePicker,
  subtitleFileInputRef,
  onUploadedSubtitleFilesChange,
  onSubtitleAssetFilenameChange,
  onSubtitleAssetContentChange,
  onRemoveSubtitleAsset,
  onAddSubtitleAsset,
  onGoToConfig,
}: {
  bookTitle: string;
  uploadedSubtitleFiles: File[];
  subtitleAssets: SubtitleAssetDraft[];
  draft: CourseDraft | null;
  slots: InputSlot[];
  isSubmitting: boolean;
  error: string | null;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onBookTitleChange: (value: string) => void;
  onOpenSubtitlePicker: () => void;
  subtitleFileInputRef: RefObject<HTMLInputElement | null>;
  onUploadedSubtitleFilesChange: (files: File[]) => void;
  onSubtitleAssetFilenameChange: (index: number, value: string) => void;
  onSubtitleAssetContentChange: (index: number, value: string) => void;
  onRemoveSubtitleAsset: (index: number) => void;
  onAddSubtitleAsset: () => void;
  onGoToConfig: () => void;
}) {
  return (
    <section className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_360px]">
      <form onSubmit={onSubmit} className="space-y-6">
        <SurfaceCard className="overflow-hidden bg-[linear-gradient(135deg,rgba(255,255,255,0.98),rgba(244,239,229,0.92))] p-6 md:p-7 xl:p-8">
          <div className="grid gap-8 xl:grid-cols-[1.1fr_0.9fr]">
            <div>
              <p className="font-stitch-label text-[11px] uppercase tracking-[0.34em] text-[var(--stitch-shell-primary-strong)]">
                Asset Forge
              </p>
              <h3 className="font-stitch-headline mt-4 text-4xl font-black tracking-[-0.05em] text-stone-900 md:text-5xl">
                ReCurr Asset Forge
              </h3>
              <p className="mt-5 max-w-2xl text-sm leading-8 text-stone-600 md:text-base">
                上传本地字幕文件、补充手工转录内容，并在进入配置页前完成课程草稿的第一轮识别。
              </p>
            </div>

            <div className="rounded-[1.75rem] bg-[var(--stitch-shell-rail)] p-5 text-stone-100 shadow-[var(--stitch-shell-shadow-strong)]">
              <p className="font-stitch-label text-[11px] uppercase tracking-[0.3em] text-white/55">
                Product Scope
              </p>
              <div className="mt-5 flex flex-wrap gap-2">
                <StatusChip label="Local Materials" tone="accent" />
                <StatusChip label="Subtitle Assets" tone="default" />
                <StatusChip label="Draft Summary" tone="default" />
              </div>
              <p className="mt-5 text-sm leading-7 text-white/72">
                当前产品路径只保留本地素材输入，不在这里引入任何外部采集入口，也不混入 preview 语义。
              </p>
            </div>
          </div>
        </SurfaceCard>

        <SurfaceCard className="p-6 md:p-7">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="font-stitch-label text-[11px] uppercase tracking-[0.28em] text-[var(--stitch-shell-primary-strong)]">
                Subtitle Assets
              </p>
              <h4 className="font-stitch-headline mt-3 text-2xl font-black tracking-[-0.04em] text-stone-900">
                本地字幕与手工转录
              </h4>
            </div>
            <StatusChip label="Runtime Ready" tone="accent" />
          </div>

          <div className="mt-6 grid gap-5">
            <label className="rounded-[1.5rem] border border-[var(--stitch-shell-border)] bg-[var(--stitch-shell-panel-soft)] px-5 py-5">
              <div className="text-sm font-semibold text-stone-700">教材名</div>
              <input
                value={bookTitle}
                onChange={(event) => onBookTitleChange(event.target.value)}
                required
                placeholder="例如：Database System Concepts"
                className="mt-3 w-full border-none bg-transparent text-sm text-stone-900 outline-none"
              />
            </label>

            <div className="rounded-[1.5rem] border border-dashed border-[var(--stitch-shell-border-strong)] bg-[var(--stitch-shell-panel-soft)] px-5 py-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold text-stone-800">上传字幕文件</div>
                  <div className="mt-1 text-xs leading-6 text-stone-500">
                    接受 `.md`、`.txt`、`text/plain`、`text/markdown`
                  </div>
                </div>
                <button
                  type="button"
                  onClick={onOpenSubtitlePicker}
                  className="rounded-full bg-[var(--stitch-shell-primary)] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[var(--stitch-shell-primary-strong)]"
                >
                  选择文件
                </button>
              </div>

              <div className="mt-4 rounded-[1.25rem] border border-white/80 bg-white/88 px-4 py-4">
                {uploadedSubtitleFiles.length > 0 ? (
                  <div className="space-y-2 text-sm text-stone-700">
                    {uploadedSubtitleFiles.map((file) => (
                      <div key={`${file.name}-${file.size}`} className="flex items-center justify-between gap-3">
                        <span className="truncate">{file.name}</span>
                        <StatusChip label="Ready" tone="accent" />
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm leading-7 text-stone-500">
                    未选择本地文件，仍可在下方手工录入字幕内容。
                  </div>
                )}
              </div>

              <input
                ref={subtitleFileInputRef}
                id="subtitle-files-input"
                type="file"
                multiple
                accept=".md,.txt,text/plain,text/markdown"
                onChange={(event: ChangeEvent<HTMLInputElement>) =>
                  onUploadedSubtitleFilesChange(Array.from(event.target.files ?? []))
                }
                className="sr-only"
              />
            </div>

            <div className="space-y-4">
              {subtitleAssets.map((asset, index) => (
                <div
                  key={`${index}-${asset.filename}`}
                  className="rounded-[1.5rem] border border-[var(--stitch-shell-border)] bg-white/90 px-5 py-5 shadow-[var(--stitch-shell-shadow-soft)]"
                >
                  <div className="flex items-center justify-between gap-3">
                    <input
                      value={asset.filename}
                      onChange={(event) => onSubtitleAssetFilenameChange(index, event.target.value)}
                      placeholder="chapter-01.md"
                      className="w-full border-none bg-transparent text-sm font-semibold text-stone-800 outline-none"
                    />
                    {subtitleAssets.length > 1 ? (
                      <button
                        type="button"
                        onClick={() => onRemoveSubtitleAsset(index)}
                        className="text-xs font-semibold uppercase tracking-[0.16em] text-stone-500 transition hover:text-stone-900"
                      >
                        Remove
                      </button>
                    ) : null}
                  </div>

                  <textarea
                    value={asset.content}
                    onChange={(event) => onSubtitleAssetContentChange(index, event.target.value)}
                    placeholder={"# 第1章 绪论\n\n这里粘贴一段字幕或转录文本。"}
                    className="mt-4 min-h-36 w-full resize-y border-none bg-transparent text-sm leading-7 text-stone-800 outline-none"
                  />
                </div>
              ))}
            </div>

            <button
              type="button"
              onClick={onAddSubtitleAsset}
              className="w-fit rounded-full border border-[var(--stitch-shell-border)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-stone-600 transition hover:bg-[var(--stitch-shell-panel-soft)]"
            >
              Add Transcript
            </button>
          </div>
        </SurfaceCard>

        <div className="grid gap-5 md:grid-cols-2">
          {slots.map((slot) => (
            <SurfaceCard key={slot.kind} className="p-5 opacity-85">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-base font-semibold text-stone-800">{slot.label}</div>
                  <div className="mt-2 text-sm leading-7 text-stone-500">
                    Coming Soon
                  </div>
                </div>
                <StatusChip
                  label={slot.supported ? `Ready · ${slot.count}` : "Coming Soon"}
                  tone={slot.supported ? "accent" : "muted"}
                />
              </div>
            </SurfaceCard>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-4">
          <button
            type="submit"
            disabled={isSubmitting}
            className="rounded-full bg-[var(--stitch-shell-primary)] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[var(--stitch-shell-primary-strong)] disabled:cursor-not-allowed disabled:opacity-60"
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
              onClick={onGoToConfig}
              className="rounded-full border border-[var(--stitch-shell-border)] px-5 py-3 text-sm font-semibold text-stone-700 transition hover:bg-[var(--stitch-shell-panel-soft)]"
            >
              前往配置页
            </button>
          ) : null}
        </div>

        {error ? (
          <div className="rounded-[1.5rem] border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        ) : null}
      </form>

      <div className="xl:self-start xl:sticky xl:top-24">
        <SurfaceCard tone="rail" className="p-6 md:p-7">
          <p className="font-stitch-label text-[11px] uppercase tracking-[0.3em] text-white/55">
            AI Insight Engine
          </p>
          <h4 className="font-stitch-headline mt-3 text-2xl font-black tracking-[-0.04em] text-white">
            课程识别摘要
          </h4>

          <ul className="mt-6 space-y-4 text-sm leading-7 text-white/76">
            <li>草稿 ID：{draft?.id ?? "尚未生成"}</li>
            <li>课程 ID：{draft?.course_id ?? "待生成"}</li>
            <li>课程名：{draft?.detected.course_name ?? "待识别"}</li>
            <li>教材名：{draft?.detected.textbook_title ?? "待填写"}</li>
            <li>
              章节结构：
              {draft?.detected.chapter_count == null ? " 待生成" : ` ${draft.detected.chapter_count}`}
            </li>
            <li>素材完整度：{draft ? ` ${draft.detected.asset_completeness}%` : " 0%"}</li>
            <li>运行就绪：{draft?.runtime_ready ? "已就绪" : "未就绪"}</li>
          </ul>
        </SurfaceCard>
      </div>
    </section>
  );
}
