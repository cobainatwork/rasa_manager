/**
 * Form field（Input / Textarea）的共用 base className。
 *
 * 抽出原因：兩個元件原本有完全重複的 ~10 段 class（焦點、aria-invalid、shake 動畫、
 * disabled 樣式）；CVA variants 會改變元件型別簽名（風險高），改為單一 const string
 * 共用，元件僅疊加自己尺寸（h-9 vs min-h-[60px]、py-1 vs py-2）等差異。
 *
 * aria-invalid 樣式：紅色邊框 + 紅 ring 漸現 + shake 動畫
 *   form 由 react-hook-form 提供 aria-invalid 屬性，會自動套用。
 *   shake-x keyframe 同時定義於 tailwind.config 與 index.css（雙保險）。
 */
export const FORM_FIELD_BASE =
  "flex w-full rounded-md border border-black/[0.12] bg-[#F2F2F7] px-3 text-sm transition-colors " +
  "placeholder:text-text-muted focus:bg-white focus-visible:outline-none " +
  "focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-0 " +
  "disabled:cursor-not-allowed disabled:opacity-40 " +
  "aria-[invalid=true]:border-destructive aria-[invalid=true]:ring-2 " +
  "aria-[invalid=true]:ring-destructive/30 aria-[invalid=true]:animate-[shake-x_360ms_ease-out]"
