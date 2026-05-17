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
  
  // Rewrites for API proxying. We split the proxy destination from
  // NEXT_PUBLIC_API_URL because that one gets baked into the client
  // bundle — when set to an internal docker hostname (e.g. http://
  // orgon-backend:8890) the browser can't resolve it. BACKEND_INTERNAL_URL
  // is server-only and lets the Next.js node process forward /api/*
  // to the backend container while the client keeps using relative URLs.
  async rewrites() {
    const apiUrl =
      process.env.BACKEND_INTERNAL_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      'http://localhost:8890';
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
      // B2B Merchant API. Lives under the operator host
      // (orgon.asystem.ai/v1/*) so integrators don't need to manage
      // a separate domain. The Node middleware excludes /v1 from the
      // auth redirect; this rewrite forwards the raw bytes to the
      // backend so HMAC verification sees the exact body the client
      // signed.
      {
        source: '/v1/:path*',
        destination: `${apiUrl}/v1/:path*`,
      },
      // WebSocket endpoint for real-time updates. Next.js rewrites
      // forward upgrade headers when the destination supports WS, so
      // /ws/updates → backend's FastAPI websocket handler at the same
      // path. Header `via: 1.1 Caddy` shows the host Caddy sits in
      // front but we proxy through Next first to keep the routing
      // single-source.
      {
        source: '/ws/:path*',
        destination: `${apiUrl}/ws/:path*`,
      },
    ];
  },
};

export default nextConfig;
