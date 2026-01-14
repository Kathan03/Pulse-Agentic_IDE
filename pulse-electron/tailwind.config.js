/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Dynamic theme colors using CSS variables
        'pulse': {
          'bg': 'var(--pulse-bg)',
          'bg-secondary': 'var(--pulse-bg-secondary)',
          'bg-tertiary': 'var(--pulse-bg-tertiary)',
          'fg': 'var(--pulse-fg)',
          'fg-muted': 'var(--pulse-fg-muted)',
          'border': 'var(--pulse-border)',
          'border-active': 'var(--pulse-border-active)',
          'input': 'var(--pulse-input)',
          'input-focus': 'var(--pulse-input-focus)',

          // Accent colors
          'primary': 'var(--pulse-primary)',
          'primary-hover': 'var(--pulse-primary-hover)',
          'success': 'var(--pulse-success)',
          'warning': 'var(--pulse-warning)',
          'error': 'var(--pulse-error)',
          'info': 'var(--pulse-info)',

          // Vibe colors (for loader)
          'vibe-thinking': 'var(--pulse-vibe-thinking)',
          'vibe-context': 'var(--pulse-vibe-context)',
          'vibe-action': 'var(--pulse-vibe-action)',

          // Selection
          'selection': 'var(--pulse-selection)',

          // Static colors that don't change with theme
          'line-number': '#858585',
          'current-line': '#282828',
        },
      },
      fontFamily: {
        'mono': ['Cascadia Code', 'Consolas', 'Menlo', 'Monaco', 'monospace'],
        'sans': ['Segoe UI', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'xxs': '0.625rem',
      },
      spacing: {
        'titlebar': '30px',
        'statusbar': '22px',
        'activitybar': '48px',
        'sidebar': '240px',
        'agentpanel': '360px',
      },
      animation: {
        'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-up': 'slideUp 0.2s ease-out',
        'vibe-pulse': 'vibePulse 1.5s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        vibePulse: {
          '0%, 100%': { transform: 'scale(1)', opacity: '1' },
          '50%': { transform: 'scale(1.15)', opacity: '0.7' },
        },
      },
      boxShadow: {
        'titlebar': '0 1px 2px rgba(0, 0, 0, 0.3)',
        'dropdown': '0 4px 16px rgba(0, 0, 0, 0.4)',
        'modal': '0 8px 32px rgba(0, 0, 0, 0.5)',
      },
    },
  },
  plugins: [],
};
