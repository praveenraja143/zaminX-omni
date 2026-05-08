/**
 * frontend/src/api_config.js
 * ==========================
 * Centralized API configuration for Zamin X.
 * Automatically switches between local development and production Render URL.
 */

// If VITE_API_URL is set in .env or Render dashboard, use it.
// Otherwise, default to your deployed backend URL.
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://zaminx-omni.onrender.com';

logger: console.log(`API Base URL: ${API_BASE_URL}`);
