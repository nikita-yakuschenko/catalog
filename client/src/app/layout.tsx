import type { Metadata } from "next";
import { Manrope } from "next/font/google";
import Link from "next/link";
import { Toaster } from "sonner";
import "./globals.css";
import { Providers } from "./providers";

const manrope = Manrope({ subsets: ["latin", "cyrillic"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "AVGST Catalog Builder",
  description: "Сборка PDF-каталогов проектов домов AVGST",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body className={`${manrope.variable} min-h-screen bg-[#F2F2EF] text-[#111] antialiased`}>
        <Providers>
          <header className="border-b border-[#D9D9D4] bg-white">
            <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
              <Link href="/" className="text-sm font-bold tracking-[0.2em] text-[#48B062] uppercase">
                AVGST Catalog Builder
              </Link>
              <nav className="flex gap-6 text-sm">
                <Link href="/projects" className="hover:text-[#48B062]">
                  Проекты
                </Link>
                <Link href="/catalogs" className="hover:text-[#48B062]">
                  Каталоги
                </Link>
                <Link href="/catalogs/new" className="hover:text-[#48B062]">
                  Новый каталог
                </Link>
              </nav>
            </div>
          </header>
          <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
          <Toaster richColors position="top-right" />
        </Providers>
      </body>
    </html>
  );
}
