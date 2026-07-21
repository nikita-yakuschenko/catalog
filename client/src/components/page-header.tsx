import type { ReactNode } from "react";
import Link from "next/link";
import { IconArrowLeft } from "@tabler/icons-react";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type PageHeaderProps = {
  backHref?: string;
  backLabel?: string;
  eyebrow?: string;
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  children?: ReactNode;
};

export function PageHeader({
  backHref,
  backLabel = "Назад",
  eyebrow,
  title,
  description,
  actions,
  children,
}: PageHeaderProps) {
  return (
    <div className="space-y-4">
      {backHref && (
        <Link
          href={backHref}
          className={cn(
            buttonVariants({ variant: "ghost", size: "sm" }),
            "-ml-2 inline-flex gap-1.5 text-muted-foreground hover:text-foreground"
          )}
        >
          <IconArrowLeft className="size-4" stroke={1.75} />
          {backLabel}
        </Link>
      )}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          {eyebrow && (
            <p className="text-xs font-medium tracking-[0.16em] text-[var(--color-brand)] uppercase">
              {eyebrow}
            </p>
          )}
          <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
          {description && <div className="text-sm text-muted-foreground">{description}</div>}
          {children}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
}
