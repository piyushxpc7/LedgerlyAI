/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  env: {
    // Production: must set NEXT_PUBLIC_API_URL at build time. No localhost default.
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? '',
  },
};

module.exports = nextConfig;
