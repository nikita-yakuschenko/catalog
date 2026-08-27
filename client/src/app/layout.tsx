import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { Toaster } from "sonner";

import { AppHeader } from "@/components/app-header";
import { cn } from "@/lib/utils";

import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Конструктор коммерческих предложений и каталогов",
  description: "Сборка PDF коммерческих предложений и каталогов проектов домов AVGST",
  icons: {
    icon: [{ url: "/icon.svg", type: "image/svg+xml" }],
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" className={cn("font-sans", GeistSans.variable)}>
      <body className={cn(GeistSans.variable, "min-h-screen antialiased")}>
        <Providers>
          <AppHeader />
          <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
          <Toaster richColors position="top-right" />
        </Providers>
      </body>
    </html>
  );
}
