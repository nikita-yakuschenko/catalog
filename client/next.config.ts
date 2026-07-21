import type { NextConfig } from "next";
import path from "node:path";
import { fileURLToPath } from "node:url";

const appRoot = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  // Monorepo-ish layout: lockfile also exists in repo root — pin Turbopack to `client/`.
  turbopack: {
    root: appRoot,
  },
};

export default nextConfig;
