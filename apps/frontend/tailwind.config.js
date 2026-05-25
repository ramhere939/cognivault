/** @type {import('tailwindcss').Config} */
// Tailwind v4: theme is now defined in index.css via @theme {}
// This file is kept only for any legacy tooling that reads it.
// Content scanning is automatic in v4.
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
}
