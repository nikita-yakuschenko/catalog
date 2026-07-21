import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Toaster } from "sonner";

import { AppHeader } from "@/components/app-header";
import { cn } from "@/lib/utils";

import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({
  subsets: ["latin", "cyrillic"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "AVGST Catalog Builder",
  description: "Сборка PDF-каталогов проектов домов AVGST",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" className={cn("font-sans", inter.variable)}>
      <body className={cn(inter.variable, "min-h-screen antialiased")}>
        <Providers>
          <AppHeader />
          <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
          <Toaster richColors position="top-right" />
        </Providers>
      </body>
    </html>
  );
}
