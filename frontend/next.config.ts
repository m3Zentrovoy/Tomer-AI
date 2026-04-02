import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/ws/:path*',
        destination: 'https://zentrovoy-tomer-ai.hf.space/ws/:path*', // Proxy to Hugging Face Backend
      },
    ];
  },
};

export default nextConfig;
