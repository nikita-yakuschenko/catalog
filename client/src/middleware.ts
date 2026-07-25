import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const SESSION_COOKIE = "avgst_session";

function authRequired(): boolean {
  const raw = (process.env.AUTH_REQUIRED || "").trim().toLowerCase();
  return raw === "1" || raw === "true" || raw === "yes";
}

export function middleware(request: NextRequest) {
  if (!authRequired()) {
    return NextResponse.next();
  }

  const { pathname } = request.nextUrl;

  // Публичные пути и прокси к API (401 отдаёт backend)
  if (
    pathname === "/login" ||
    pathname === "/health" ||
    pathname === "/icon.svg" ||
    pathname === "/favicon.ico" ||
    pathname.startsWith("/api/") ||
    pathname.startsWith("/storage/") ||
    pathname.startsWith("/output/") ||
    pathname.startsWith("/_next/")
  ) {
    return NextResponse.next();
  }

  const session = request.cookies.get(SESSION_COOKIE)?.value;
  if (!session) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.search = "";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image).*)"],
};
