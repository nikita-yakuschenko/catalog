import Link from "next/link";

export default function HomePage() {
  return (
    <div className="space-y-8">
      <div className="max-w-2xl space-y-4">
        <p className="text-xs font-semibold tracking-[0.2em] text-[#48B062] uppercase">
          Publishing pipeline
        </p>
        <h1 className="text-4xl font-semibold tracking-tight">Сборка каталогов AVGST</h1>
        <p className="text-[#737373] leading-relaxed">
          Синхронизация проектов с avgst.ru, выбор состава, детерминированные композиции
          и генерация экранного PDF в стиле корпоративного каталога.
        </p>
      </div>
      <div className="flex flex-wrap gap-3">
        <Link
          href="/projects"
          className="rounded-md bg-[#48B062] px-5 py-3 text-sm font-medium text-white"
        >
          Проекты
        </Link>
        <Link
          href="/catalogs/new"
          className="rounded-md border border-[#D9D9D4] bg-white px-5 py-3 text-sm font-medium"
        >
          Создать каталог
        </Link>
      </div>
    </div>
  );
}
