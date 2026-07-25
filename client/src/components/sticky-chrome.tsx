"use client";

import { useLayoutEffect, useRef, type ReactNode } from "react";

import { cn } from "@/lib/utils";

type StickyChromeProps = {
  children: ReactNode;
  className?: string;
};

/** Закрепляет шапку страницы / фильтры сразу под AppHeader; пишет --page-chrome-height. */
export function StickyChrome({ children, className }: StickyChromeProps) {
  const ref = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;

    const apply = () => {
      document.documentElement.style.setProperty("--page-chrome-height", `${el.offsetHeight}px`);
    };
    apply();
    const ro = new ResizeObserver(apply);
    ro.observe(el);
    return () => {
      ro.disconnect();
      document.documentElement.style.setProperty("--page-chrome-height", "0px");
    };
  }, []);

  return (
    <div
      ref={ref}
      className={cn(
        "sticky z-40 -mx-6 space-y-6 bg-background px-6 pb-4",
        className
      )}
      style={{ top: "var(--app-header-height)" }}
    >
      {children}
    </div>
  );
}
