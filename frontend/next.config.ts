import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  eslint: {
    // Suppress ESLint checks during build to prevent build failures on auto-generated template rules
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Allow production builds to complete even if there are minor TypeScript warnings
    ignoreBuildErrors: false,
  },
};

export default nextConfig;
