"use client";

import Link from "next/link";

import { StitchV4TopNav } from "@/components/stitch-v4/chrome";
import { StitchV4MaterialSymbol } from "@/components/stitch-v4/material-symbol";
import { useLocale } from "@/lib/locale";
import { buildProductHref, type ProductContext } from "@/lib/product-nav";

function ActionCard({
  number,
  title,
  description,
  status,
  href,
  icon,
  accent = false,
}: {
  number: string;
  title: string;
  description: string;
  status: string;
  href: string;
  icon: string;
  accent?: boolean;
}) {
  return (
    <Link
      href={href}
      className={`group relative flex min-h-[260px] flex-col justify-between rounded-[2rem] p-7 transition-all duration-300 ${
        accent
          ? "bg-[var(--stitch-inverse-surface)] text-white shadow-[var(--stitch-shell-shadow-strong)]"
          : "bg-[var(--stitch-surface-container-lowest)] text-[var(--stitch-on-surface)] shadow-[var(--stitch-shell-shadow-soft)] hover:shadow-[var(--stitch-shell-shadow)]"
      }`}
    >
      <div>
        <div className="mb-5 flex items-start justify-between">
          <span
            className={`font-stitch-headline text-3xl font-black ${
              accent
                ? "text-[#dddad0]"
                : "text-[var(--stitch-surface-container-highest)] group-hover:text-[rgba(29,109,255,0.14)]"
            }`}
          >
            {number}
          </span>
          <div
            className={`rounded-xl p-3 ${
              accent
                ? "bg-[var(--stitch-primary)] text-white"
                : "bg-[var(--stitch-surface-container-high)] text-[var(--stitch-primary)]"
            }`}
          >
            <StitchV4MaterialSymbol name={icon} />
          </div>
        </div>
        <h3 className="font-stitch-headline text-2xl font-extrabold">{title}</h3>
        <p
          className={`mt-2 text-sm ${
            accent ? "text-[#dddad0]" : "text-[var(--stitch-on-secondary-container)]"
          }`}
        >
          {description}
        </p>
      </div>
      <div
        className="mt-8 flex items-center justify-between pt-6"
      >
        <span
          className={`rounded-lg px-3 py-1 text-[11px] font-bold uppercase tracking-wider ${
            accent
              ? "bg-[#474746] text-[#dddad0]"
              : "bg-[var(--stitch-surface-container-high)] text-[var(--stitch-on-surface-variant)]"
          }`}
        >
          {status}
        </span>
        <StitchV4MaterialSymbol
          name={accent ? "rocket_launch" : "arrow_forward"}
          className={accent ? "text-white" : "text-[var(--stitch-primary)]"}
        />
      </div>
    </Link>
  );
}

export function StitchV4OverviewPage({
  context,
}: {
  context: ProductContext;
}) {
  const { messages } = useLocale();
  return (
    <div className="min-h-screen bg-[var(--stitch-surface-container-low)] text-[var(--stitch-on-surface)]">
      <StitchV4TopNav active="overview" context={context} />
      <main className="mx-auto max-w-7xl px-6 py-10 md:py-14">
        <section className="mx-auto mb-14 flex max-w-3xl flex-col items-center text-center">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-[var(--stitch-surface-container-high)] px-4 py-1.5 text-xs font-bold uppercase tracking-[0.2em] text-[var(--stitch-primary)]">
            {messages.overview.badge}
          </div>
          <h1 className="font-stitch-headline mb-6 text-4xl font-extrabold leading-[1.05] tracking-[-0.08em] md:text-6xl">
            {messages.overview.titleLeading} <br />
            <span className="text-[var(--stitch-primary)]">{messages.overview.titleAccent}</span>
          </h1>
          <p className="mb-8 max-w-2xl text-lg leading-relaxed text-[var(--stitch-on-secondary-container)] md:text-xl">
            {messages.overview.description}
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link
              href={buildProductHref("input", context)}
              className="rounded-xl bg-gradient-to-r from-[var(--stitch-primary)] to-[var(--stitch-primary-container)] px-8 py-4 font-bold text-white shadow-lg shadow-[rgba(0,85,212,0.2)] transition-all duration-300 hover:scale-[0.98]"
            >
              {messages.overview.launch}
            </Link>
            <Link
              href={buildProductHref("results", context)}
              className="rounded-xl bg-[var(--stitch-inverse-surface)] px-8 py-4 font-bold text-[var(--stitch-inverse-on-surface)] transition-all hover:bg-[#42423a]"
            >
              {messages.overview.openResults}
            </Link>
          </div>
        </section>

        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-4">
          <ActionCard
            number="01"
            title={messages.overview.cards.input.title}
            description={messages.overview.cards.input.description}
            status={context.draftId ? messages.overview.cards.input.ready : messages.overview.cards.input.waiting}
            href={buildProductHref("input", context)}
            icon="input"
          />
          <ActionCard
            number="02"
            title={messages.overview.cards.config.title}
            description={messages.overview.cards.config.description}
            status={context.draftId ? messages.overview.cards.config.ready : messages.overview.cards.config.waiting}
            href={buildProductHref("config", context)}
            icon="settings_input_component"
          />
          <ActionCard
            number="03"
            title={messages.overview.cards.run.title}
            description={messages.overview.cards.run.description}
            status={context.runId ? messages.overview.cards.run.active : messages.overview.cards.run.waiting}
            href={buildProductHref("run", context)}
            icon="play_arrow"
            accent
          />
          <ActionCard
            number="04"
            title={messages.overview.cards.results.title}
            description={messages.overview.cards.results.description}
            status={context.courseId ? messages.overview.cards.results.ready : messages.overview.cards.results.waiting}
            href={buildProductHref("results", context)}
            icon="task_alt"
          />
        </div>
      </main>
    </div>
  );
}
