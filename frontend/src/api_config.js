/**
 * frontend/src/api_config.js
 * ==========================
 * Centralized API configuration for Zamin X.
 * Automatically switches between local development and production Render URL.
 */

// In development (local), use localhost:8000
// In production (Render), VITE_API_URL will be set to the backend URL
const isDev = import.meta.env.DEV;

export const API_BASE_URL = import.meta.env.VITE_API_URL || 
  (isDev ? 'http://localhost:8000' : 'https://zaminx-omni.onrender.com');

console.log(`[Zamin X] API Base URL: ${API_BASE_URL}`);
