import type { Config } from 'tailwindcss'
import tailwindcssAnimate from 'tailwindcss-animate'

const config: Config = {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx,js,jsx}'],
  theme: {
    container: { center: true, padding: '1rem' },
    extend: {
      colors: {
        // macOS-inspired design tokens
        brand: {
          50: '#EAF4FF',
          100: '#C5E2FF',
          500: '#007AFF',   // Apple system blue
          600: '#0066CC',
          700: '#0052A3',
        },
        canvas: '#F2F2F7',        // macOS system background
        surface: '#FFFFFF',
        subtle: '#E5E5EA',        // macOS secondary fill
        'text-primary': '#1C1C1E',
        'text-secondary': '#3C3C43',
        'text-muted': '#636366',  // macOS tertiary label
        'border-default': '#D1D1D6',  // macOS separator
        'border-strong': '#AEAEB2',
        // shadcn 必要色票（對應 index.css 的 CSS 變數）
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
      },
      fontFamily: {
        // 字型 fallback 策略（瀏覽器 per-character lookup）：
        //   英數：Inter（已由 @fontsource/inter 載入）→ 系統 sans
        //   中文：macOS PingFang TC → Windows 11 Microsoft JhengHei UI →
        //         Windows 10 Microsoft JhengHei → Linux Noto Sans CJK / Noto Sans TC
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          'SF Pro Text',
          '"Segoe UI"',
          '"PingFang TC"',
          '"Microsoft JhengHei UI"',
          '"Microsoft JhengHei"',
          '"Noto Sans CJK TC"',
          '"Noto Sans TC"',
          'system-ui',
          'sans-serif',
        ],
        mono: ['SF Mono', 'JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      transitionDuration: {
        instant: '100ms',
        fast: '150ms',
        base: '200ms',
        slow: '300ms',
      },
      transitionTimingFunction: {
        'out-soft': 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
      zIndex: {
        dropdown: '10',
        sticky: '20',
        overlay: '30',
        modal: '40',
        toast: '50',
        tooltip: '60',
      },
      boxShadow: {
        xs: '0 1px 2px rgba(0,0,0,0.06)',
        sm: '0 1px 4px rgba(0,0,0,0.08), 0 0 0 1px rgba(0,0,0,0.04)',
        md: '0 4px 12px rgba(0,0,0,0.10), 0 1px 3px rgba(0,0,0,0.06)',
        lg: '0 8px 28px rgba(0,0,0,0.12), 0 3px 8px rgba(0,0,0,0.06)',
        window: '0 20px 60px rgba(0,0,0,0.15), 0 2px 6px rgba(0,0,0,0.08)',
      },
      keyframes: {
        'accordion-down': { from: { height: '0' }, to: { height: 'var(--radix-accordion-content-height)' } },
        'accordion-up': { from: { height: 'var(--radix-accordion-content-height)' }, to: { height: '0' } },
      },
      animation: {
        'accordion-down': 'accordion-down 200ms ease-out',
        'accordion-up': 'accordion-up 200ms ease-out',
      },
    },
  },
  plugins: [tailwindcssAnimate],
}

export default config
