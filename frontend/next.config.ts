import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // An unrelated lockfile exists above this repository on the development machine.
  // Keep file tracing inside this frontend rather than treating the user directory as a monorepo.
  outputFileTracingRoot: process.cwd(),
};

export default nextConfig;
