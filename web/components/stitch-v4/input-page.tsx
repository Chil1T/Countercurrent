"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { StitchV4ContextRail } from "@/components/stitch-v4/context-rail";
import { StitchV4RightRail, StitchV4TopNav } from "@/components/stitch-v4/chrome";
import { StitchV4MaterialSymbol } from "@/components/stitch-v4/material-symbol";
import { createCourseDraft, getCourseDraft, type CourseDraft } from "@/lib/api/course-drafts";
import { useLocale } from "@/lib/locale";
import type { ProductContext } from "@/lib/product-nav";

type SubtitleAssetDraft = {
  filename: string;
  content: string;
};

const defaultSlots = [
  { kind: "subtitle", supported: true, count: 0 },
  { kind: "audio_video", supported: false, count: 0 },
  { kind: "courseware", supported: false, count: 0 },
  { kind: "textbook", supported: true, count: 0 },
];

export function StitchV4InputPage({
  initialDraftId,
  context,
}: {
  initialDraftId: string | null;
  context: ProductContext;
}) {
  const { messages } = useLocale();
  const router = useRouter();
  const subtitleFileInputRef = useRef<HTMLInputElement | null>(null);
  const [bookTitle, setBookTitle] = useState("");
  const [uploadedSubtitleFiles, setUploadedSubtitleFiles] = useState<File[]>([]);
  const [subtitleAssets, setSubtitleAssets] = useState<SubtitleAssetDraft[]>([
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
      const preparedAssets = subtitleAssets.filter(
        (asset) => asset.filename.trim() && asset.content.trim().length > 0,
      );
      const formData = new FormData();
      formData.append("book_title", bookTitle);

      for (const file of uploadedSubtitleFiles) {
        formData.append("subtitle_files", file, file.name);
      }
      for (const asset of preparedAssets) {
        const blob = new Blob([asset.content], { type: "text/markdown" });
        formData.append("subtitle_files", blob, asset.filename);
      }

      const nextDraft =
        uploadedSubtitleFiles.length > 0 || preparedAssets.length > 0
          ? await createCourseDraft(formData)
          : await createCourseDraft({ book_title: bookTitle });
      setDraft(nextDraft);
      router.replace(
        `/courses/new/input?draftId=${encodeURIComponent(nextDraft.id)}&courseId=${encodeURIComponent(nextDraft.course_id)}`,
      );
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unknown error");
    } finally {
      setIsSubmitting(false);
    }
  }

  const slots = (draft?.input_slots ?? defaultSlots)
    .filter((slot) => slot.kind !== "course_link")
    .map((slot) => ({
      ...slot,
      label:
        messages.input.slotLabels[
          slot.kind as keyof typeof messages.input.slotLabels
        ] ?? ("label" in slot && typeof slot.label === "string" ? slot.label : slot.kind),
    }));
  const nextContext = {
    draftId: draft?.id ?? context.draftId,
    courseId: draft?.course_id ?? context.courseId,
    runId: context.runId,
  };

  return (
    <div className="min-h-screen bg-[var(--stitch-background)] text-[var(--stitch-on-surface)]">
      <StitchV4TopNav active="input" context={nextContext} />
      <main className="flex min-h-[calc(100vh-64px)] pr-80">
        <form className="mx-auto w-full max-w-5xl flex-1 px-10 py-10" onSubmit={handleSubmit}>
          <header className="mb-12">
            <h1 className="font-stitch-headline mb-4 text-5xl font-extrabold tracking-[-0.08em]">
              {messages.input.title}
            </h1>
            <p className="max-w-2xl text-lg leading-relaxed text-[var(--stitch-on-surface-variant)]">
              {messages.input.subtitle}
            </p>
          </header>

          <div className="grid grid-cols-12 gap-8">
            <div className="col-span-12">
              <label className="mb-3 block text-xs font-bold uppercase tracking-[0.24em] text-[var(--stitch-on-surface-variant)]">
                {messages.input.textbookLabel}
              </label>
              <div className="rounded-xl bg-[var(--stitch-surface-container-high)] p-1">
                <input
                  className="w-full border-none bg-transparent px-6 py-4 text-xl font-medium outline-none placeholder:text-[rgba(66,70,85,0.45)]"
                  placeholder={messages.input.textbookPlaceholder}
                  value={bookTitle}
                  onChange={(event) => setBookTitle(event.target.value)}
                />
              </div>
            </div>

            <div className="col-span-12">
              <label className="mb-3 block text-xs font-bold uppercase tracking-[0.24em] text-[var(--stitch-on-surface-variant)]">
                {messages.input.subtitleLabel}
              </label>
              <div className="relative flex h-56 flex-col items-center justify-center rounded-[1rem] bg-[var(--stitch-surface-container-lowest)] shadow-[var(--stitch-shell-shadow-soft)] transition-all hover:bg-[rgba(29,109,255,0.02)]">
                <div className="mb-4 rounded-full bg-[rgba(0,85,212,0.1)] p-4">
                  <StitchV4MaterialSymbol
                    name="upload_file"
                    className="text-3xl text-[var(--stitch-primary)]"
                  />
                </div>
                <p className="text-lg font-semibold">{messages.input.dropTitle}</p>
                <p className="mt-1 text-sm text-[var(--stitch-on-surface-variant)]">
                  {messages.input.dropSubtitle}
                </p>
                <button
                  type="button"
                  className="mt-5 rounded-xl bg-[var(--stitch-inverse-surface)] px-6 py-2 font-medium text-white transition-all active:scale-95"
                  onClick={() => subtitleFileInputRef.current?.click()}
                >
                  {messages.input.selectFiles}
                </button>
                <input
                  ref={subtitleFileInputRef}
                  id="subtitle-files-input"
                  type="file"
                  accept=".srt,.vtt,.md,.txt"
                  multiple
                  className="hidden"
                  onChange={(event) =>
                    setUploadedSubtitleFiles(Array.from(event.target.files ?? []))
                  }
                />
              </div>
            </div>

            <div className="col-span-12 mt-2">
              <div className="mb-6 flex items-center justify-between">
                <h3 className="font-stitch-headline text-3xl font-bold">{messages.input.queueTitle}</h3>
                <span className="rounded-lg bg-[var(--stitch-surface-container-high)] px-3 py-1 text-xs font-bold uppercase tracking-wider text-[var(--stitch-on-surface-variant)]">
                  {uploadedSubtitleFiles.length +
                    subtitleAssets.filter((asset) => asset.content.trim()).length}{" "}
                  {messages.input.readyCount}
                </span>
              </div>

              <div className="space-y-4">
                {uploadedSubtitleFiles.map((file) => (
                  <div
                    key={file.name}
                    className="flex items-center justify-between rounded-xl bg-[var(--stitch-surface-container-lowest)] p-6 transition-all hover:shadow-xl hover:shadow-[rgba(28,28,22,0.05)]"
                  >
                    <div className="flex items-center gap-5">
                      <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-[var(--stitch-surface-container)]">
                        <StitchV4MaterialSymbol
                          name="subtitles"
                          className="text-[var(--stitch-on-surface-variant)]"
                        />
                      </div>
                      <div>
                        <h4 className="font-semibold">{file.name}</h4>
                        <p className="mt-0.5 text-xs text-[var(--stitch-on-surface-variant)]">
                          {(file.size / 1024).toFixed(1)} KB · {messages.input.localUpload}
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      className="text-[var(--stitch-on-surface-variant)] transition-colors hover:text-[var(--stitch-error)]"
                      onClick={() =>
                        setUploadedSubtitleFiles((current) =>
                          current.filter((item) => item.name !== file.name),
                        )
                      }
                    >
                      <StitchV4MaterialSymbol name="delete" />
                    </button>
                  </div>
                ))}

                {subtitleAssets.map((asset, index) => (
                  <div
                    key={`${asset.filename}-${index}`}
                    className="rounded-xl bg-[var(--stitch-surface-container-lowest)] p-6"
                  >
                    <div className="mb-4 flex items-center justify-between gap-4">
                      <input
                        className="min-w-0 flex-1 border-none bg-transparent text-base font-semibold outline-none"
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
                      />
                      <button
                        type="button"
                        className="text-[var(--stitch-on-surface-variant)] transition-colors hover:text-[var(--stitch-error)]"
                        onClick={() =>
                          setSubtitleAssets((current) =>
                            current.filter((_, itemIndex) => itemIndex !== index),
                          )
                        }
                      >
                        <StitchV4MaterialSymbol name="delete" />
                      </button>
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
                      className="min-h-32 w-full rounded-xl border border-[var(--stitch-outline-variant)] bg-[var(--stitch-surface-container-low)] px-4 py-3 text-sm outline-none"
                      placeholder={messages.input.manualPlaceholder}
                    />
                  </div>
                ))}
              </div>

              <div className="mt-6 flex items-center justify-between">
                <button
                  type="button"
                  className="rounded-full border border-[var(--stitch-outline-variant)] px-6 py-3 text-sm font-bold text-[var(--stitch-on-surface)]"
                  onClick={() =>
                    setSubtitleAssets((current) => [
                      ...current,
                      {
                        filename: `chapter-${String(current.length + 1).padStart(2, "0")}.md`,
                        content: "",
                      },
                    ])
                  }
                >
                  {messages.input.addManualTranscript}
                </button>
                <div className="flex items-center gap-4">
                  {draft ? (
                    <button
                      type="button"
                      className="rounded-full px-6 py-3 text-sm font-bold text-[var(--stitch-primary)]"
                      onClick={() =>
                        router.push(
                          `/courses/new/config?draftId=${encodeURIComponent(draft.id)}&courseId=${encodeURIComponent(draft.course_id)}`,
                        )
                      }
                    >
                      {messages.input.continueToConfig}
                    </button>
                  ) : null}
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="rounded-full bg-gradient-to-r from-[var(--stitch-primary)] to-[var(--stitch-primary-container)] px-10 py-3 font-bold text-white shadow-lg shadow-[rgba(0,85,212,0.2)] transition-all disabled:opacity-60"
                  >
                    {isSubmitting ? messages.input.saving : messages.input.saveAndDetect}
                  </button>
                </div>
              </div>

              {error ? (
                <div className="mt-4 rounded-xl bg-[var(--stitch-error-container)] px-4 py-3 text-sm text-[var(--stitch-on-error-container)]">
                  {error}
                </div>
              ) : null}
            </div>
          </div>
        </form>

        <StitchV4RightRail title={messages.common.context} subtitle={messages.common.activeSession}>
          <StitchV4ContextRail
            draftId={draft?.id ?? context.draftId}
            courseId={draft?.course_id ?? context.courseId}
            runId={context.runId}
            prefix={
              <section className="rounded-xl bg-[#474746] p-5">
                <h3 className="mb-4 text-xs font-bold uppercase tracking-widest text-[#dddad0]/70">
                  {messages.input.inputModes}
                </h3>
                <ul className="space-y-2 text-sm text-[#f4f1e7]">
                  {slots.map((slot) => (
                    <li key={slot.kind}>
                      {slot.label} · {slot.supported ? messages.input.supported : messages.input.comingSoon} · {slot.count}
                    </li>
                  ))}
                </ul>
              </section>
            }
          />
        </StitchV4RightRail>
      </main>
    </div>
  );
}
