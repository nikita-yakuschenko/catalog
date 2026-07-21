import Link from "next/link";
import { IconBooks, IconFolder } from "@tabler/icons-react";

import { buttonVariants } from "@/components/ui/button";
import { PageHeader } from "@/components/page-header";
import { cn } from "@/lib/utils";

export default function HomePage() {
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Publishing pipeline"
        title="Сборка каталогов AVGST"
        description={
          <>
            Синхронизация проектов с avgst.ru, выбор состава, детерминированные композиции и генерация
            экранного PDF в стиле корпоративного каталога.
          </>
        }
      />
      <div className="flex flex-wrap gap-3">
        <Link href="/projects" className={cn(buttonVariants({ size: "lg" }))}>
          <IconFolder className="size-4" stroke={1.75} />
          Проекты
        </Link>
        <Link href="/catalogs/new" className={cn(buttonVariants({ variant: "outline", size: "lg" }))}>
          <IconBooks className="size-4" stroke={1.75} />
          Создать каталог
        </Link>
      </div>
    </div>
  );
}
