import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone", // small runtime image for the Docker deployment
};

export default nextConfig;
