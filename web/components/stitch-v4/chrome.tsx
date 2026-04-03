import Image from "next/image";
import Link from "next/link";
import { ReactNode } from "react";

import { StitchV4MaterialSymbol } from "@/components/stitch-v4/material-symbol";
import { useLocale } from "@/lib/locale";
import { buildProductNav, type ProductContext, type ProductNavKey } from "@/lib/product-nav";

function activeLinkClass(active: boolean): string {
  if (active) {
    return "rounded-full bg-[var(--stitch-shell-primary-soft)] px-4 py-2 text-[var(--stitch-shell-primary)] shadow-[var(--stitch-shell-shadow-soft)]";
  }
  return "rounded-full px-4 py-2 text-[var(--stitch-on-secondary-container)] transition-colors duration-200 hover:bg-[var(--stitch-surface-container-high)] hover:text-[var(--stitch-primary)]";
}

export function StitchV4TopNav({
  active,
  context,
  withSearch = false,
}: {
  active: ProductNavKey;
  context: ProductContext;
  withSearch?: boolean;
}) {
  const { locale, toggleLocale, messages } = useLocale();
  const navItems = buildProductNav(context);

  return (
    <header className="sticky top-0 z-50 flex w-full items-center justify-between bg-[var(--stitch-shell-panel)] px-8 py-2.5 backdrop-blur-2xl shadow-[var(--stitch-shell-shadow-soft)]">
      <div className="flex items-center gap-6">
        <Link href="/" className="flex items-center gap-3">
          <Image
            src="/brand/recurr-logo.svg"
            alt=""
            aria-hidden="true"
            width={58}
            height={58}
            className="h-[58px] w-[58px]"
          />
          <div>
            <span className="font-stitch-headline block text-2xl font-black leading-none tracking-[-0.08em] text-[var(--stitch-primary)]">
              {messages.brand.title}
            </span>
            <span className="block pt-1 text-[10px] font-semibold uppercase leading-none tracking-[0.24em] text-[var(--stitch-on-surface-variant)]">
              {messages.brand.tagline}
            </span>
          </div>
        </Link>
        <nav className="hidden items-center gap-2 md:flex">
          {navItems.map((item) => (
            <Link
              key={item.key}
              href={item.href}
              className={`text-sm font-semibold ${activeLinkClass(item.key === active)}`}
            >
              {messages.nav[item.key]}
            </Link>
          ))}
        </nav>
      </div>

      <div className="flex items-center gap-4">
        {withSearch ? (
          <div className="hidden items-center rounded-full bg-[var(--stitch-surface-container-lowest)] px-4 py-1.5 shadow-[var(--stitch-shell-shadow-soft)] lg:flex">
            <StitchV4MaterialSymbol name="search" className="mr-2 text-sm text-[var(--stitch-on-surface-variant)]" />
            <input
              readOnly
              value=""
              placeholder={messages.brand.searchPlaceholder}
              className="w-40 border-none bg-transparent text-sm text-[var(--stitch-on-surface-variant)] outline-none placeholder:text-[var(--stitch-on-surface-variant)]"
            />
          </div>
        ) : null}
        <button
          type="button"
          onClick={toggleLocale}
          className="rounded-full bg-[var(--stitch-surface-container-lowest)] px-3 py-1.5 text-xs font-bold text-[var(--stitch-on-surface-variant)] shadow-[var(--stitch-shell-shadow-soft)]"
          aria-label={locale === "zh-CN" ? "切换到英文" : "Switch to Chinese"}
        >
          {messages.brand.localeLabel}
        </button>
        <button type="button" className="rounded-full bg-[var(--stitch-surface-container-lowest)] p-1.5 text-[var(--stitch-on-surface-variant)] shadow-[var(--stitch-shell-shadow-soft)]">
          <StitchV4MaterialSymbol name="notifications" />
        </button>
        <button type="button" className="rounded-full bg-[var(--stitch-surface-container-lowest)] p-1.5 text-[var(--stitch-on-surface-variant)] shadow-[var(--stitch-shell-shadow-soft)]">
          <StitchV4MaterialSymbol name="settings" />
        </button>
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--stitch-secondary-fixed)] text-[11px] font-bold text-[var(--stitch-on-surface-variant)] shadow-[var(--stitch-shell-shadow-soft)]">
          UI
        </div>
      </div>
    </header>
  );
}

export function StitchV4RightRail({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <aside className="fixed right-0 top-0 flex h-screen w-80 flex-col bg-[var(--stitch-inverse-surface)] pt-20 text-[var(--stitch-inverse-on-surface)] shadow-[var(--stitch-shell-shadow-strong)]">
      <div className="px-8 py-6">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="font-stitch-headline text-xl font-bold">{title}</h2>
          <StitchV4MaterialSymbol name="analytics" className="text-xl text-[var(--stitch-primary)]" />
        </div>
        <p className="text-xs opacity-70">{subtitle}</p>
      </div>
      <div className="flex-1 overflow-y-auto px-4 pb-8">{children}</div>
    </aside>
  );
}
