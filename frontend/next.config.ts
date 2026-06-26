import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  output: "standalone",
  // Allow cross-origin requests from the Docker backend
  async rewrites() {
    return []
  },
}

export default nextConfig
