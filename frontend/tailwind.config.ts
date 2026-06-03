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
        // 文字色軟化：從 macOS 純灰調轉向 slate 冷調（含 hint of blue），
        // 大面積閱讀更柔和、整體質感更現代（避免「死黑 + 中性灰」的廉價感）。
        'text-primary': '#11182C',    // 介於 slate-900 與 macOS label 之間
        'text-secondary': '#374151',  // slate-700
        'text-muted': '#64748B',      // slate-500（原 macOS tertiary 偏暖）
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
        // 雙層光源陰影（ambient + key light），用 slate-900 rgb(15,23,42)
        // 取代純黑 — 帶輕微冷色，避免「廉價硬黑」陰影，整體更高級。
        xs: '0 1px 1px rgba(15,23,42,0.04), 0 0 1px rgba(15,23,42,0.04)',
        sm: '0 1px 2px rgba(15,23,42,0.04), 0 2px 6px rgba(15,23,42,0.04)',
        md: '0 2px 4px rgba(15,23,42,0.04), 0 8px 20px rgba(15,23,42,0.06)',
        lg: '0 4px 8px rgba(15,23,42,0.04), 0 16px 40px rgba(15,23,42,0.08)',
        window: '0 8px 24px rgba(15,23,42,0.06), 0 32px 72px rgba(15,23,42,0.12)',
      },
      keyframes: {
        'accordion-down': { from: { height: '0' }, to: { height: 'var(--radix-accordion-content-height)' } },
        'accordion-up': { from: { height: 'var(--radix-accordion-content-height)' }, to: { height: '0' } },
        // Form 錯誤 shake — 配合 aria-invalid 在 Input/Textarea 套用，
        // 位移 4px、總長 360ms；prefers-reduced-motion 已由 index.css 全域抑制。
        'shake-x': {
          '0%, 100%': { transform: 'translateX(0)' },
          '20%, 60%': { transform: 'translateX(-4px)' },
          '40%, 80%': { transform: 'translateX(4px)' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 200ms ease-out',
        'accordion-up': 'accordion-up 200ms ease-out',
        'shake-x': 'shake-x 360ms ease-out',
      },
    },
  },
  plugins: [tailwindcssAnimate],
}

export default config
