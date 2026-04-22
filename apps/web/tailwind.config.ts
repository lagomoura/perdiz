import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          orange: {
            100: 'rgb(var(--brand-orange-100) / <alpha-value>)',
            500: 'rgb(var(--brand-orange-500) / <alpha-value>)',
            600: 'rgb(var(--brand-orange-600) / <alpha-value>)',
          },
          graphite: {
            700: 'rgb(var(--brand-graphite-700) / <alpha-value>)',
            900: 'rgb(var(--brand-graphite-900) / <alpha-value>)',
          },
        },
        neutral: {
          0: 'rgb(var(--neutral-0) / <alpha-value>)',
          50: 'rgb(var(--neutral-50) / <alpha-value>)',
          100: 'rgb(var(--neutral-100) / <alpha-value>)',
          200: 'rgb(var(--neutral-200) / <alpha-value>)',
          400: 'rgb(var(--neutral-400) / <alpha-value>)',
          600: 'rgb(var(--neutral-600) / <alpha-value>)',
          900: 'rgb(var(--neutral-900) / <alpha-value>)',
        },
        success: { 500: 'rgb(var(--success-500) / <alpha-value>)' },
        warning: { 500: 'rgb(var(--warning-500) / <alpha-value>)' },
        error: { 500: 'rgb(var(--error-500) / <alpha-value>)' },
        info: { 500: 'rgb(var(--info-500) / <alpha-value>)' },
      },
      fontFamily: {
        display: ['var(--font-display)'],
        body: ['var(--font-body)'],
        mono: ['var(--font-mono)'],
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        xl: 'var(--radius-xl)',
      },
      boxShadow: {
        sm: 'var(--shadow-sm)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
        focus: 'var(--shadow-focus)',
      },
      transitionTimingFunction: {
        'in-out-smooth': 'cubic-bezier(0.2, 0.8, 0.2, 1)',
      },
    },
  },
  plugins: [],
} satisfies Config;
