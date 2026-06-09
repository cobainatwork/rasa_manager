type AppLogoSize = 'sm' | 'lg'

const LOGO_SRC = '/hualiteq.png'
const BRAND_NAME = 'Hualiteq KB'

const SIZE_MAP = {
  sm: { dim: 24, gap: 'gap-2', img: 'w-6 h-6', text: 'font-medium text-[13px] text-text-primary tracking-tight' },
  lg: { dim: 40, gap: 'gap-3', img: 'w-10 h-10', text: 'text-xl font-semibold' },
} as const

export function AppLogo({ size = 'sm' }: { size?: AppLogoSize }) {
  const s = SIZE_MAP[size]
  return (
    <div className={`flex items-center ${s.gap}`}>
      <img src={LOGO_SRC} alt="Hualiteq" width={s.dim} height={s.dim} className={`${s.img} object-contain`} />
      <span className={s.text}>{BRAND_NAME}</span>
    </div>
  )
}
