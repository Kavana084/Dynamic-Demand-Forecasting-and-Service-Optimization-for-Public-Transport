/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        /* Smart Transit token-backed colors (no hardcoded product colors in components) */
        background: 'var(--st-bg)',
        surface: 'var(--st-surface)',
        sidebar: 'var(--st-sidebar)',
        ink: 'var(--st-ink)',
        muted: 'var(--st-muted)',
        'muted-2': 'var(--st-muted-2)',
        border: 'var(--st-border)',
        primary: 'var(--st-primary)',
        secondary: 'var(--st-secondary)',
        'accent-cyan': 'var(--st-accent-cyan)',
        'accent-indigo': 'var(--st-accent-indigo)',
        success: 'var(--st-success)',
        warning: 'var(--st-warning)',
        danger: 'var(--st-danger)',
        info: 'var(--st-info)',
      },
      fontFamily: {
        sans: ['var(--st-font-sans)', 'system-ui', 'sans-serif'],
        mono: ['var(--st-font-mono)', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      boxShadow: {
        'st-sm': 'var(--st-shadow-sm)',
        'st-md': 'var(--st-shadow-md)',
      },
    },
  },
  plugins: [],
}
