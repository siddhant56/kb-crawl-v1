/** @type {import('next').NextConfig} */
const config = {
  // All backend calls go through Next.js API routes, so no rewrites needed.
  // SERVER-SIDE env var — never exposed to browser:
  //   API_BASE_URL = http://localhost:8000
  // Shared env var (must also be in .env.local):
  //   AUTH_JWT_SECRET = (same value as backend AUTH_JWT_SECRET)
};

module.exports = config;
