/**
 * Tailwind config for Face Sort Studio.
 * Mirrors the old cdn.tailwindcss.com inline config so the compiled,
 * vendored CSS is visually identical — but works fully offline.
 * Build with:  npm run build:css   (see package.json)
 */
module.exports = {
  darkMode: 'class',
  content: [
    './face_sort/app/templates/**/*.html',
    './face_sort/app/static/js/**/*.js',
  ],
  // Classes assembled at runtime in app.js (e.g. `bg-${c.color}/10`) can't be
  // discovered by content scanning, so list them explicitly.
  safelist: [
    'bg-apple-blue/10', 'bg-apple-green/10', 'bg-apple-indigo/10', 'bg-apple-orange/10',
    'text-apple-blue', 'text-apple-green', 'text-apple-indigo', 'text-apple-orange',
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ['"SF Pro Display"', '"Helvetica Neue"', 'Helvetica', 'Arial', 'sans-serif'],
        body: ['"SF Pro Text"', '"Helvetica Neue"', 'Helvetica', 'Arial', 'sans-serif'],
      },
      colors: {
        apple: {
          blue: '#007AFF',
          indigo: '#5856D6',
          purple: '#AF52DE',
          pink: '#FF2D55',
          red: '#FF3B30',
          orange: '#FF9500',
          yellow: '#FFCC00',
          green: '#34C759',
          teal: '#5AC8FA',
          gray: {
            50: '#F9FAFB',
            100: '#F2F2F7',
            200: '#E5E5EA',
            300: '#D1D1D6',
            400: '#AEAEB2',
            500: '#8E8E93',
            600: '#636366',
            700: '#48484A',
            800: '#2C2C2E',
            900: '#1C1C1E',
          },
        },
      },
      borderRadius: {
        'apple': '12px',
        'apple-lg': '16px',
        'apple-xl': '20px',
      },
      boxShadow: {
        'apple': '0 1px 3px rgba(0,0,0,0.08), 0 4px 12px rgba(0,0,0,0.05)',
        'apple-md': '0 2px 8px rgba(0,0,0,0.08), 0 8px 24px rgba(0,0,0,0.06)',
        'apple-lg': '0 4px 16px rgba(0,0,0,0.1), 0 12px 40px rgba(0,0,0,0.08)',
        'apple-hover': '0 6px 20px rgba(0,0,0,0.12), 0 16px 48px rgba(0,0,0,0.1)',
      },
    },
  },
  plugins: [],
}
