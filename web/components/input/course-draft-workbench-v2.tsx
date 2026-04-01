"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import {
  CourseDraft,
  createCourseDraft,
  getCourseDraft,
} from "@/lib/api/course-drafts";
import { InputV2Sections, SubtitleAssetDraft } from "@/components/input/input-v2-sections";

const defaultSlots = [
  { kind: "subtitle", label: "字幕", supported: true, count: 0 },
  { kind: "audio_video", label: "音视频", supported: false, count: 0 },
  { kind: "courseware", label: "课件", supported: false, count: 0 },
  { kind: "textbook", label: "教材", supported: true, count: 0 },
];

export function CourseDraftWorkbenchV2({
  initialDraftId,
}: {
  initialDraftId: string | null;
}) {
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
      setError(submitError instanceof Error ? submitError.message : "Unknown error");
    } finally {
      setIsSubmitting(false);
    }
  }

  const slots = (draft?.input_slots ?? defaultSlots).filter((slot) => slot.kind !== "course_link");

  return (
    <InputV2Sections
      bookTitle={bookTitle}
      uploadedSubtitleFiles={uploadedSubtitleFiles}
      subtitleAssets={subtitleAssets}
      draft={draft}
      slots={slots}
      isSubmitting={isSubmitting}
      error={error}
      onSubmit={handleSubmit}
      onBookTitleChange={setBookTitle}
      onOpenSubtitlePicker={() => subtitleFileInputRef.current?.click()}
      subtitleFileInputRef={subtitleFileInputRef}
      onUploadedSubtitleFilesChange={setUploadedSubtitleFiles}
      onSubtitleAssetFilenameChange={(index, value) =>
        setSubtitleAssets((current) =>
          current.map((item, itemIndex) =>
            itemIndex === index ? { ...item, filename: value } : item,
          ),
        )
      }
      onSubtitleAssetContentChange={(index, value) =>
        setSubtitleAssets((current) =>
          current.map((item, itemIndex) =>
            itemIndex === index ? { ...item, content: value } : item,
          ),
        )
      }
      onRemoveSubtitleAsset={(index) =>
        setSubtitleAssets((current) => current.filter((_, itemIndex) => itemIndex !== index))
      }
      onAddSubtitleAsset={() =>
        setSubtitleAssets((current) => [
          ...current,
          {
            filename: `chapter-${String(current.length + 1).padStart(2, "0")}.md`,
            content: "",
          },
        ])
      }
      onGoToConfig={() => {
        if (draft) {
          router.push(`/courses/new/config?draftId=${draft.id}`);
        }
      }}
    />
  );
}
