import type { NextConfig } from "next";
import path from "node:path";
import { fileURLToPath } from "node:url";

const appRoot = path.dirname(fileURLToPath(import.meta.url));

const backend = process.env.BACKEND_URL || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // Tunnel hosts (ngrok / localhost.run / cloudflare) — иначе Next 16 режет /_next и dev-запросы
  allowedDevOrigins: [
    "*.ngrok-free.app",
    "*.ngrok.io",
    "*.lhr.life",
    "*.localhost.run",
    "*.trycloudflare.com",
    "*.loca.lt",
  ],
  // Monorepo-ish layout: lockfile also exists in repo root — pin Turbopack to `client/`.
  turbopack: {
    root: appRoot,
  },
  // Same-origin proxy so one tunnel to :3000 reaches the API too.
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${backend}/api/:path*` },
      { source: "/storage/:path*", destination: `${backend}/storage/:path*` },
      { source: "/output/:path*", destination: `${backend}/output/:path*` },
      { source: "/health", destination: `${backend}/health` },
    ];
  },
};

export default nextConfig;
