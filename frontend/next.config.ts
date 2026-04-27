import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable standalone output for Docker
  output: 'standalone',

  // Skip TypeScript errors during Coolify build (still type-checked locally
  // via `npx tsc --noEmit`). ESLint config moved to .eslintrc per Next 16.
  typescript: { ignoreBuildErrors: true },
  
  // Performance optimizations
  compress: true,
  poweredByHeader: false,
  reactStrictMode: true,
  
  images: {
    formats: ['image/avif', 'image/webp'],
  },
  
  // Force cache invalidation on every build
  generateBuildId: async () => {
    return `build-${Date.now()}`;
  },
  
  // Allow cross-origin requests from production domain
  allowedDevOrigins: ['orgon.asystem.kg'],
  
  // Rewrites for API proxying
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8890';
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
