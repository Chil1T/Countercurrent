import Link from "next/link";

import { AppShell } from "@/components/app-shell";
import { buildAppShellState } from "@/lib/app-shell-state";

export default function Home() {
  const shellState = buildAppShellState("/", new URLSearchParams());

  return (
    <AppShell eyebrow="Overview" title="Course Production Workbench" shellState={shellState}>
      <section className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-[28px] border border-stone-200 bg-stone-50 p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-stone-500">
            Mission
          </p>
          <h3 className="mt-3 max-w-2xl text-3xl font-semibold tracking-tight">
            把 blueprint-first CLI 包装成一个面向课程生产者的 Web 产品。
          </h3>
          <p className="mt-4 max-w-2xl text-base leading-8 text-stone-600">
            第一版聚焦四个动作：组织输入、配置模板、理解运行状态、检查知识包结果。
            页面结构先稳定下来，再逐步接入真实 API 与 runtime。
          </p>

          <div className="mt-8 grid gap-4 md:grid-cols-2">
            {[
              "输入页按多模态分区设计，当前先支持字幕与教材。",
              "配置页是核心，决定产物长什么样。",
              "运行页展示阶段轨道与 resumable 状态。",
              "结果页是文件树 + 预览 + reviewer 的三栏工作台。",
            ].map((item) => (
              <div
                key={item}
                className="rounded-2xl border border-stone-200 bg-white px-4 py-4 text-sm leading-7 text-stone-700"
              >
                {item}
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-[28px] border border-stone-200 bg-[#15120f] p-6 text-stone-100">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-stone-400">
            Next Steps
          </p>
          <div className="mt-5 space-y-3">
            {shellState.navItems.map((item) =>
              item.enabled && item.href ? (
                <Link
                  key={item.label}
                  href={item.href}
                  className="block rounded-2xl border border-white/10 bg-white/6 px-4 py-4 transition hover:bg-white/10"
                >
                  <div className="text-base font-medium">打开{item.label}页</div>
                  <div className="mt-1 text-sm text-stone-400">{item.hint}</div>
                </Link>
              ) : (
                <div
                  key={item.label}
                  className="rounded-2xl border border-dashed border-white/10 bg-white/4 px-4 py-4 text-stone-500"
                >
                  <div className="text-base font-medium">打开{item.label}页</div>
                  <div className="mt-1 text-sm">需要先创建真实草稿或运行会话</div>
                </div>
              ),
            )}
          </div>
        </div>
      </section>
    </AppShell>
  );
}
