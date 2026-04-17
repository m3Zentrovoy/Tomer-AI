import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/ws/:path*',
        destination: 'https://tomer-ai-production-fe51.up.railway.app/ws/:path*', // Proxy to Railway Backend
      },
      {
        source: '/api/:path*',
        destination: 'https://tomer-ai-production-fe51.up.railway.app/api/:path*', // Proxy API to Railway Backend
      },
    ];
  },
};

export default nextConfig;
