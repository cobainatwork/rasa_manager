# 前端 UI/UX 全面重構設計文件

**日期：** 2026-04-30
**範圍：** Rasa RAG 知識庫管理平台 — 前端
**負責人：** 待指派
**狀態：** Draft（待使用者審閱）

---

## 0. 摘要

現有前端為「能跑就好」的 MVP 實作，存在多項嚴重 UX 反模式：新增 FAQ 流程使用三段式瀏覽器原生 `prompt()` 對話框、AgentSelect 卡片暴露技術路徑當主資訊、Dashboard 僅有 7 個冷數字無趨勢無行動入口、各頁無導航層次、空狀態與載入狀態統一是純文字。本次重構解決 P0 + P1 等級問題，採三欄式（Notion / Linear 風）主從畫面、shadcn/ui 元件庫、Inter + JetBrains Mono 字型、Tailwind CSS variables 設計 token，全程 inline 互動（除少數白名單刪除確認）。

---

## 1. 設計目標與成功標準

### 1.1 目標
- 消除瀏覽器原生 `prompt()`、所有 FAQ 操作 inline 完成
- 類別樹直接可視 + 直接可編輯，廢除獨立 `/categories` 路由
- FAQ 主畫面從表格升級為三欄主從（左樹｜中列表｜右詳情）
- 所有頁面建立明確視覺層次（Topbar / Sidebar / Breadcrumb）
- 建立可維護的設計 token 系統，支援未來 dark mode

### 1.2 成功標準
- 新使用者可在無教學情況下完成「建立分類 → 新增 FAQ → 送審」流程
- 所有清單頁面顯示 skeleton loading（廢除「載入中...」純文字）
- TypeScript `tsc --noEmit` 零錯誤
- Vitest coverage ≥ 70%
- 鍵盤可達成所有核心操作（不需滑鼠）
- WCAG 2.1 AA 合規（focus ring / 對比度 / aria-label）

### 1.3 不在範圍（Out of Scope）
- Dark mode（token 預備、Phase 1 不交付）
- Mobile 支援（< 1024px 顯示警告，內部工具不主推）
- 後端 API 大改動（僅新增 `GET sync/history` 一個端點）
- 國際化 i18n（介面語言固定繁體中文）

---

## 2. 硬約束（Hard Constraints）

來自使用者明確指示，不可違反：

1. **樹狀結構直接可視 + 直接可編輯** — 類別樹不能藏在 modal 或獨立頁
2. **新增 / 編輯不開新視窗** — FAQ、分類、使用者、Agent 的新增與編輯一律 inline
3. **遵守 clean-code 原則** — 元件 ≤ 150 行、props ≤ 5 個、function 單一職責、F.I.R.S.T. 測試
4. **完全禁用 emoji 當 UI 圖示** — 一律 Lucide React，stroke-width 1.5
5. **完全廢除 index.css 中手刻的 `.btn-*` `.badge-*` `.card` `.input`**
6. **所有設計值來自 token scale**，禁止寫 `padding: 13px` 等自訂數字

「不開新視窗」原則的**唯一例外**：高風險不可逆動作（刪除 Agent / User / FAQ / 含 FAQ 的分類 / 強取編輯鎖）— 此 5 場景准用 shadcn `AlertDialog`。

---

## 3. 資訊架構與全站導航

### 3.1 路由結構

| 路徑 | 說明 |
|------|------|
| `/login` | 登入 |
| `/agents` | Agent 選擇（卡片牆） |
| `/admin/users` | 使用者管理（僅 Superadmin） |
| `/agents/:id/dashboard` | 儀表板 |
| `/agents/:id/knowledge` | 知識庫主畫面（三欄、含類別樹） |
| `/agents/:id/sync` | 同步任務 |
| `/agents/:id/import-export` | 匯入匯出 |
| `/agents/:id/audit` | 稽核日誌 |
| `/agents/:id/test-chat` | 對話測試 |
| `/agents/:id/settings` | Agent 設定（僅 Superadmin） |

**廢除路由：** `/agents/:id/categories` — 併入 `/agents/:id/knowledge` 三欄左側。

### 3.2 全站版面骨架

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 64px Topbar:  [Logo] Rasa KB / Rasa_Demo_Bot ▾ / 知識庫     🔔 admin ▾ │
├──────┬───────────────────────────────────────────────────────────────────┤
│ 64px │                                                                   │
│ Side │                                                                   │
│ Nav  │                  主內容區（依路由切換）                             │
│      │                                                                   │
└──────┴───────────────────────────────────────────────────────────────────┘
```

**Topbar 元素**：Logo / Agent 切換器（dropdown）/ Breadcrumb / 通知 / 帳號選單
**Sidebar**：64px 寬度、icon-only、hover 顯示中文 tooltip

### 3.3 左側 Nav 圖示順序

| Lucide Icon | 路由 | 說明 | 顯示條件 |
|-------------|------|------|---------|
| `Home` | dashboard | 儀表板 | 一律顯示 |
| `BookOpen` | knowledge | 知識庫 | 一律顯示 |
| `RefreshCw` | sync | 同步 | 一律顯示 |
| `ArrowDownUp` | import-export | 匯入匯出 | 一律顯示 |
| `MessageSquare` | test-chat | 對話測試 | 一律顯示 |
| `History` | audit | 稽核日誌 | 一律顯示 |
| `Settings` | settings | Agent 設定 | 僅 Superadmin |

### 3.4 RWD 斷點

| 寬度 | 行為 |
|------|------|
| ≥ 1280px | 三欄完整顯示（240 / flex / 480） |
| 1024–1280px | 右欄收摺，點選列表項目以 drawer 滑入 |
| < 1024px | 顯示警告：「請使用桌面瀏覽，建議寬度 1280px 以上」 |

---

## 4. KnowledgeBase 三欄主畫面（核心改造）

### 4.1 整體 Wireframe

```
┌─────────────────┬───────────────────────┬───────────────────────────┐
│ 類別樹 (240px)   │ FAQ 列表 (flex)        │ FAQ 詳情/編輯 (480px)      │
│                 │                       │                           │
│ ▾ 產品功能 (45) │ ⌕ 搜尋  [篩選▾]      │ ◉ 如何重設密碼?            │
│   ▸ 帳號 (12)  │ ☐ 問題           狀態 v│ 問題（click to edit）     │
│   ▾ 安全 (18)  │ ☑ 如何重設密碼? 已核准 3│ 答案（Markdown 編輯器）   │
│   ⓦ 密碼 (8)● │ ☐ 兩步驟驗證... 待審核 1│ 分類: 產品功能/安全/密碼   │
│   ⓦ 隱私 (5)  │ ☐ 帳號被鎖定...  已同步 2│ 標籤: [密碼][登入]         │
│ ▸ 訂閱 (15)    │ ☐ 修改 Email   草稿 1 │ 狀態: 已核准                │
│ ▸ 計費 (22)    │                       │ ─── 操作 ───              │
│ ▸ 客服 (8)     │ [上一頁] 1/4 [下一頁]  │ [送審] [退回] [刪除]       │
│ + 新增根類別    │                       │ ─── 版本歷史 (3) ───      │
│                 │                       │ ▾ v3 admin 1h 前 編輯     │
│                 │                       │ ▸ v2 admin 2d 前 退回     │
│                 │                       │ ▸ v1 admin 3d 前 建立     │
└─────────────────┴───────────────────────┴───────────────────────────┘
```

### 4.2 左欄：類別樹（CategoryTree）

| 操作 | 互動 | 視覺回饋 |
|------|------|---------|
| 單擊節點 | 選取此分類，過濾右欄 FAQ 列表 | 整列藍色背景 + 左 3px 藍邊 |
| 雙擊名稱 | inline rename，文字變 input | 輸入框取代文字、autofocus + 全選 |
| hover 節點 | 右側出現 ⋯ icon | popover menu: 重新命名 / 新增子分類 / 刪除 |
| `+ 新增根類別` | 樹頂部按鈕 | 新節點預設名「未命名分類」 |
| ▸ / ▾ 圖示 | 收合/展開子節點 | 整體動畫 200ms ease-out |
| (數字) | 該分類下 FAQ 數量 | 灰色小字、自動忽略 0 |

**Clean code 約束：**
- `CategoryTree.tsx` 只負責渲染，不直接呼叫 API
- 邏輯抽 `useCategoryTree()` hook：`tree`, `selectedId`, `select(id)`, `rename(id, name)`, `addChild(parentId)`, `remove(id)`
- 單一節點抽 `CategoryTreeNode.tsx`（遞迴渲染）
- 純函式 `buildCategoryTree(flat: Category[]): CategoryNode[]` 在 `lib/categories.ts`

**拖曳節點重排父子關係**：列為 Phase 2，**不在本次範圍**。

### 4.3 中欄：FAQ 列表（FaqList）

```
┌────────────────────────────────────────────────────────────────────┐
│ ⌕ 搜尋問題或答案...                          [篩選 ▾]  [+ 新增 FAQ]│
├────────────────────────────────────────────────────────────────────┤
│ Active filters:  ⓧ 狀態:已核准    ⓧ 分類:產品功能/安全          │
├────────────────────────────────────────────────────────────────────┤
│ ☐ │ 問題                                       │ 狀態   │ v  │ 鎖 │
│───┼────────────────────────────────────────────┼────────┼────┼────│
│ ☑ │ 如何重設密碼?                              │ 已核准 │ v3 │    │
│ ☐ │ 兩步驟驗證如何啟用?                        │ 待審核 │ v1 │ 🔒 │
│ ☐ │ 帳號被鎖定怎麼處理?                        │ 已同步 │ v2 │    │
│   │ #密碼 #登入                                │        │    │    │
└────────────────────────────────────────────────────────────────────┘
```

**功能元素：**
- 搜尋框：即時搜尋 question + answer，300ms debounce
- 篩選 popover：status / tags / 編輯鎖狀態 / 建立者 / 日期區間
- Active filter chip：點 `ⓧ` 移除單一條件
- Checkbox 多選：bulk action bar 浮現於頂部
- 整列點擊：選中此筆，右欄載入詳情（不跳頁）
- 右鍵選單（context menu）：依當前狀態動態顯示送審/核准/退回/刪除
- `🔒` 圖示：編輯鎖中，hover tooltip 顯示鎖定者名稱
- `#tag` 點擊 → 加入 active filter
- 鍵盤 ↑↓：切換選中列；Enter：進入編輯模式（焦點移至右欄問題欄）

**URL 同步**：`?status=approved&category=xxx&q=密碼` — 重新整理保留狀態、可分享連結

### 4.4 右欄：FAQ 詳情/編輯（FaqDetail）

**核心模式：所有欄位都是 click-to-edit，無編輯/檢視切換按鈕**

| 欄位 | 編輯模式 | 儲存時機 |
|------|---------|---------|
| 問題 | 點擊 → textarea | blur 自動儲存（300ms debounce）+ Cmd+Enter 立即儲存 |
| 答案 | 點擊 → Markdown 編輯器（@uiw/react-md-editor），可切 Edit / Preview / Split | 同上 |
| 分類 | 點擊 → Combobox（shadcn `Command`），可搜尋樹狀路徑 | 選擇後立即儲存 |
| 標籤 | tag chips + `+` 按鈕 | 新增/刪除立即儲存 |
| 狀態 | badge 不可直接點，只能透過下方「操作」按鈕轉換 | 按下按鈕後送 API |

**頂部狀態列（sticky）：**
```
◉ 如何重設密碼?      [儲存中...] / [✓ 已儲存 14:23] / [⚠ 儲存失敗 重試]
```

**操作按鈕區（依當前 status 動態顯示，符合狀態機）：**

| 當前 status | 顯示的按鈕（依角色） |
|------------|------------------|
| `draft` | [送審]（editor/superadmin）/ [刪除]（owner/superadmin） |
| `pending` | [核准] [退回]（reviewer/superadmin） |
| `rejected` | [重新送審]（editor）/ [刪除] |
| `approved` | [取消核准]（superadmin） |
| `synced` | （唯讀，編輯後自動降級為 draft） |

**Empty state（未選 FAQ 時）：**
```
        📄 (Lucide FileText)
   選擇左側一筆 FAQ
   以檢視與編輯詳情
   ────────────
   [+ 新增第一筆 FAQ]
```

### 4.5 版本歷史與 Diff（位於右欄底部）

**版本歷史 vs 稽核日誌的明確區分：**

| 項目 | 版本歷史 | 稽核日誌 |
|------|----------|---------|
| 資料表 | `knowledge_item_histories` | `audit_logs` |
| 範圍 | 單一 FAQ 的編輯版本鏈 | 全系統所有動作 |
| 位置 | 右欄 FAQ 詳情面板**底部** | 獨立頁面 `/agents/:id/audit` |
| 支援 rollback | ✅ | ❌ |

**版本歷史互動：**
- 預設折疊，只顯示最近 3 筆，避免長 FAQ 詳情卷軸過長
- 每筆預覽 1 行：`v{n} {使用者} {相對時間} {動作}`
- 點 `▸` 展開該版本 → 顯示變更欄位的 inline diff（紅刪線 / 綠加底）
- `[👁 完整 diff]` 按鈕 → 在右欄頂部覆蓋全寬比對視圖（current vs 該版本，左右並排）
- `[↶ 還原]` 按鈕 → inline 確認列「確定還原至 v2？目前內容會變成新版本 v4。[確認] [取消]」（不開 modal）
- `[展開完整歷史]` → 動態載入所有版本

**Clean code 約束：**
- `VersionTimeline.tsx`（折疊清單）
- `VersionDiffView.tsx`（全寬 diff）
- `useFaqHistory(faqId)` hook
- 純函式 `lib/diff.ts`：`computeDiff(prev, current)` 回傳 `{ field, before, after }[]`，配 vitest 測試

### 4.6 鍵盤快捷鍵全表

| 鍵 | 動作 | 焦點區域 |
|----|------|---------|
| `/` | 聚焦搜尋框 | 全域 |
| `n` | 新增 FAQ | 全域 |
| `↑` / `↓` | 切換選中列 | 中欄 list |
| `Enter` | 進入編輯（焦點跳右欄問題欄） | 中欄 list |
| `j` / `k` | 同 ↓ / ↑（vim 風） | 中欄 list |
| `x` | 切換 checkbox | 中欄 list |
| `g` `g` | 跳至首列 | 中欄 list |
| `G` | 跳至末列 | 中欄 list |
| `Esc` | 取消編輯 / 關閉篩選器 | 任何輸入框 |
| `Cmd/Ctrl + S` | 立即儲存 | 右欄編輯欄位 |
| `Cmd/Ctrl + Enter` | 儲存並跳下一筆 | 右欄編輯欄位 |
| `?` | 顯示快捷鍵速查表 | 全域 |

### 4.7 三欄寬度與互動

- 左欄 240px：固定寬，可摺疊為 0（icon 切換）
- 中欄 flex：自動延展
- 右欄 480px：可拖拉調整 360–600px，記憶到 localStorage
- 欄位之間 1px 細分隔線（slate-200），hover 出現 4px 拖拉熱區（cursor: col-resize）

---

## 5. Design Tokens

### 5.1 色彩系統

#### 主色（Brand / Blue）
| Token | Hex | 用途 |
|-------|-----|------|
| `--brand-50` | `#EFF6FF` | hover 背景、selected row |
| `--brand-500` | `#3B82F6` | 主按鈕、品牌主色 |
| `--brand-600` | `#2563EB` | 主按鈕 hover |
| `--brand-700` | `#1D4ED8` | 主按鈕 active |

#### 中性色（Neutral / Slate）
| Token | Hex | 用途 |
|-------|-----|------|
| `--bg-canvas` | `#F8FAFC` | 頁面背景 |
| `--bg-surface` | `#FFFFFF` | 卡片/面板背景 |
| `--bg-subtle` | `#F1F5F9` | hover 背景、區塊分隔 |
| `--border-default` | `#E2E8F0` | 一般邊框 |
| `--border-strong` | `#CBD5E1` | 表單 input 邊框 |
| `--text-primary` | `#0F172A` | 主要文字（WCAG AAA） |
| `--text-secondary` | `#475569` | 次要文字（4.5:1 對比下限） |
| `--text-muted` | `#64748B` | 提示、placeholder |

#### 狀態語意色（FAQ status mapping）
| Status | Bg | Text | Border |
|--------|------|------|--------|
| `draft` | `#F1F5F9` (slate-100) | `#475569` (slate-600) | `#CBD5E1` |
| `pending` | `#FEF3C7` (amber-100) | `#92400E` (amber-800) | `#FCD34D` |
| `approved` | `#D1FAE5` (emerald-100) | `#065F46` (emerald-800) | `#6EE7B7` |
| `rejected` | `#FEE2E2` (red-100) | `#991B1B` (red-800) | `#FCA5A5` |
| `synced` | `#DBEAFE` (blue-100) | `#1E40AF` (blue-800) | `#93C5FD` |

#### 通用語意色
| Token | Hex | 用途 |
|-------|-----|------|
| `--success` | `#10B981` | 儲存成功、核准 |
| `--warning` | `#F59E0B` | 編輯鎖、未儲存變更 |
| `--danger` | `#EF4444` | 刪除、退回、錯誤 |
| `--info` | `#3B82F6` | 提示、版本歷史 |
| `--cta` | `#F97316` | 強調行動按鈕（onboarding 空狀態） |

#### 焦點環
- 一律 `focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2`
- 對比度 ≥ 3:1

### 5.2 字型系統

| 角色 | 字型 |
|------|------|
| Sans（heading + body） | `Inter` |
| 中文 fallback | `Noto Sans TC` |
| Mono（程式碼、UUID、timestamp、kbd） | `JetBrains Mono` |

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Noto+Sans+TC:wght@400;500;700&display=swap');

:root {
  --font-sans: 'Inter', 'Noto Sans TC', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', Consolas, monospace;
}
```

#### 字型尺寸 scale
| Token | Size / Line-height | 用途 |
|-------|-------------------|------|
| `text-xs` | 12px / 16px | 標籤、metadata、badge |
| `text-sm` | 14px / 20px | 表格、表單、次要文字 |
| `text-base` | 16px / 24px | body |
| `text-lg` | 18px / 28px | 卡片標題 |
| `text-xl` | 20px / 28px | 區塊標題 |
| `text-2xl` | 24px / 32px | 頁面標題 |
| `text-3xl` | 30px / 36px | 大數字（Dashboard KPI） |

#### 字重
- `400` body / `500` label、按鈕 / `600` 標題、表格標頭 / `700` 大數字、強調

#### Line-height
- body 文字：`1.5–1.75`
- 段落最大字元數：`max-w-[65ch]`

### 5.3 間距系統（4px base grid）

| Token | px | 用途 |
|-------|----|----|
| `space-1` | 4 | 小元件內距 |
| `space-2` | 8 | 圖示與文字間距、tag 間距 |
| `space-3` | 12 | 表格 cell 內距 |
| `space-4` | 16 | 卡片內距、段落間距 |
| `space-6` | 24 | 區塊間距 |
| `space-8` | 32 | 頁面 padding、section 間距 |
| `space-12` | 48 | 大區塊分隔 |

**強制規則：** 所有間距值必須來自此 scale，禁寫 `padding: 13px`。

### 5.4 圓角系統

| Token | px | 用途 |
|-------|----|----|
| `rounded-sm` | 4 | tag、small badge |
| `rounded-md` | 6 | input、button |
| `rounded-lg` | 8 | card、modal |
| `rounded-xl` | 12 | 大卡片、image |
| `rounded-full` | 9999 | avatar、status dot |

避免 `rounded-2xl` 以上。

### 5.5 陰影系統

```css
--shadow-xs: 0 1px 2px 0 rgb(0 0 0 / 0.05);
--shadow-sm: 0 1px 3px 0 rgb(0 0 0 / 0.07), 0 1px 2px -1px rgb(0 0 0 / 0.05);
--shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.08), 0 2px 4px -2px rgb(0 0 0 / 0.05);
--shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.05);
```

| Token | 用途 |
|-------|------|
| `shadow-xs` | 一般卡片 |
| `shadow-sm` | hover 提升、popover |
| `shadow-md` | dropdown menu、tooltip |
| `shadow-lg` | dialog、command palette |

禁用 `shadow-2xl`。

### 5.6 動畫 / motion

| Token | Duration | Easing | 用途 |
|-------|---------|--------|------|
| `--motion-instant` | `100ms` | `ease-out` | 按鈕按下、checkbox |
| `--motion-fast` | `150ms` | `ease-out` | hover、focus、color transition |
| `--motion-base` | `200ms` | `ease-out` | dropdown、popover、tab |
| `--motion-slow` | `300ms` | `cubic-bezier(0.4, 0, 0.2, 1)` | dialog、drawer、page transition |

**強制規則：**
- 入場 `ease-out`、退場 `ease-in`
- 禁用 `linear`
- 禁用 > `500ms` 動畫
- 必須支援 `prefers-reduced-motion: reduce`：
  ```css
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: 0.01ms !important;
      transition-duration: 0.01ms !important;
    }
  }
  ```

### 5.7 Z-index scale

| Token | Value | 用途 |
|-------|-------|------|
| `z-base` | `0` | 一般元素 |
| `z-dropdown` | `10` | dropdown、popover |
| `z-sticky` | `20` | sticky header、breadcrumb |
| `z-overlay` | `30` | drawer 背景遮罩 |
| `z-modal` | `40` | dialog、command palette |
| `z-toast` | `50` | toast notification |
| `z-tooltip` | `60` | tooltip（永遠在最上層） |

禁寫 `z-index: 9999`。

### 5.8 圖示系統

- 完全禁用 emoji 當 UI 圖示
- 統一使用 Lucide React
- 統一 size：`w-4 h-4` 內聯、`w-5 h-5` 按鈕、`w-6 h-6` 導覽
- 統一 stroke-width：`1.5`

### 5.9 互動規則

- 所有可點擊元素加 `cursor-pointer`
- hover 必有視覺回饋（color / shadow / border 至少一項變化）
- 點擊區大小 ≥ 44×44px

### 5.10 Tailwind config 落地

`tailwind.config.ts` 擴充 theme：
```ts
extend: {
  colors: {
    brand: { 50: '#EFF6FF', 500: '#3B82F6', 600: '#2563EB', 700: '#1D4ED8' },
    canvas: '#F8FAFC',
    surface: '#FFFFFF',
    'border-default': '#E2E8F0',
  },
  fontFamily: {
    sans: ['Inter', 'Noto Sans TC', 'system-ui', 'sans-serif'],
    mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
  },
  transitionDuration: {
    instant: '100ms', fast: '150ms', base: '200ms', slow: '300ms',
  },
  zIndex: {
    dropdown: '10', sticky: '20', overlay: '30',
    modal: '40', toast: '50', tooltip: '60',
  },
}
```

`index.css` 廢除手刻 `.btn-*` `.badge-*` `.card` `.input`，全改用 shadcn 元件。

---

## 6. 其他頁面改造

### 6.1 Login

**現況問題：** 白卡置中、零品牌識別。

**新版設計：** 左右分割 60/40

- 左：品牌區（漸層背景 brand-500 → brand-700），顯示 Logo、產品名、3 條賣點
- 右：登入表單（白色），含密碼 show/hide eye icon、Rate limit 觸發顯示倒數
- < 1024px 自動隱藏品牌區、表單置中

### 6.2 AgentSelect

**現況問題：** 卡片暴露 `txt_output_path`、`rasa_rest_url` 技術路徑當主資訊。

**新版設計：**
- 卡片只顯示對使用者有意義的指標：FAQ 總數、待審核數、最後同步時間
- 角色 badge（自己在此 Agent 的權限）
- 技術設定移到 Agent Settings 頁
- `+ 建立 Agent` 點擊 → inline expand panel（不開 modal）
- 廢除 `CreateAgentModal.tsx`，改為 `CreateAgentInlinePanel.tsx`

### 6.3 Dashboard

**現況問題：** 7 個冷數字、無趨勢、無行動入口。

**新版設計：** 三區塊
- 上：KPI 列（4 卡），顯示對昨日差量
- 中左：「待我處理」面板，依角色篩選，可 inline 審核
- 中右：「最近活動」timeline，取自 audit_logs
- 下：「快速操作」按鈕列（新增 FAQ / 觸發同步 / 對話測試）

### 6.4 SyncPage

**現況問題：** 只看到「當前任務」，沒歷史。

**新版設計：**
- 上：觸發新同步 + 進行中橫幅
- 下：歷史紀錄 timeline（最近 20 筆），整列點擊 expand 顯示 stdout/stderr
- 失敗項目「重新觸發」按鈕
- **新增後端端點 `GET /api/v1/agents/:id/sync/history`**

### 6.5 ImportExport

**新版設計：**
- 左右分欄：匯入 / 匯出
- 拖放 dropzone（react-dropzone）
- 進度條：上傳 → 解析 → 寫入三階段
- 結果區 inline 顯示（成功 / 跳過 / 失敗 + 列號），失敗列號可跳到該 FAQ

### 6.6 AuditLog

**新版設計：**
- 篩選 bar：日期區間 / 使用者 / 動作類型
- 依日期 group by（今天 / 昨天 / 本週 / 更早）
- diff 展開：JSON 並排對照
- 點 FAQ 名稱 → 跳到該筆 FAQ 詳情

### 6.7 TestChat

**新版設計：**
- 標準 chat bubble UI（左：使用者、右：Bot）
- Bot 訊息 hover 出「複製」按鈕
- typing 動畫（三個跳動點）
- `Cmd/Ctrl + Enter` 送出
- 清除對話按鈕（重置 sender_id）

### 6.8 AgentSettings

**新版設計：**
- 分區表單：基本資訊 / Rasa 整合 / Ingestion 腳本 / 危險區
- Sticky 變更橫幅（`[⚠ 未儲存變更] [儲存]`）
- 「測試連線」按鈕（送 GET 至 webhook）
- 「驗證腳本存在性」按鈕（呼叫後端檢查 file exists）
- 危險區：刪除 Agent，使用 shadcn `AlertDialog` 簡化版確認

### 6.9 UserManagement

**新版設計：** 左右分欄 master-detail
- 左：使用者列表 + 搜尋 + `+ 新增使用者` inline 表單
- 右：選中使用者詳情、各 Agent 角色 dropdown 自動儲存、危險區（重設密碼 / 停用）

---

## 7. 錯誤 / 空狀態 / 載入狀態 / Toast

### 7.1 載入狀態（廢除「載入中...」純文字）

| 類型 | 場景 | 元件 |
|------|------|------|
| Skeleton | 列表 / 表格類 | shadcn `Skeleton` + `animate-pulse` |
| Spinner | 短暫操作（< 1s） | Lucide `Loader2` + `animate-spin` |
| Progress Bar | 已知進度（Excel 匯入三階段） | shadcn `Progress` |

### 7.2 錯誤狀態（四級）

| 級別 | 場景 | 元件 |
|------|------|------|
| P0 Inline | 表單欄位錯誤 | 欄位下方紅字 |
| P1 區塊 | 資料載入失敗 | shadcn `Alert variant="destructive"` |
| P2 Toast | 操作失敗 | sonner（右下，自動消失 5s） |
| P3 全頁 | 500 / 路由不存在 | 獨立錯誤頁 + 返回按鈕 |

### 7.3 空狀態（四種，禁純文字「無資料」）

| 類型 | 場景 | 設計 |
|------|------|------|
| First-time | 從未建立 | Lucide icon + 引導文字 + CTA 按鈕 |
| Filtered | 篩選結果為空 | 搜尋 icon + 「清除所有篩選」按鈕 |
| Done | 待處理為零 | 勾選 icon + 正向回饋 |
| Unselected | 右欄未選 | 文件 icon + 引導文字 |

### 7.4 Toast 系統

`<Toaster />` 放 `App.tsx` root（pro-max shadcn 規則：禁止每頁放）

| 類型 | 圖示 | 顏色 | 持續時間 |
|------|------|------|---------|
| Success | `CircleCheck` | emerald-600 | 3s |
| Error | `CircleX` | red-600 | 5s |
| Warning | `TriangleAlert` | amber-600 | 4s |
| Info | `Info` | blue-600 | 3s |

**規則：**
- 同類訊息合併
- 可手動關閉
- Action button 可選（如「重新嘗試」、「復原」）
- 不搶焦點（避免打斷輸入）

### 7.5 確認對話框白名單（5 場景）

允許使用 shadcn `AlertDialog` 的場景：
1. 刪除 Agent
2. 刪除使用者
3. 刪除 FAQ
4. 刪除分類（且分類下有 FAQ）
5. 強制取消他人編輯鎖

**簡化版確認對話框（不要求輸入名稱）：**
```
┌──────────────────────────────────┐
│  ⚠ 確認刪除？                     │
│  將刪除 Rasa_Demo_Bot 及其下：     │
│   • 152 筆 FAQ                    │
│   • 12 個分類                      │
│   • 88 筆稽核日誌                  │
│  此操作無法復原。                  │
│       [取消]   [永久刪除]          │
└──────────────────────────────────┘
```

- `[永久刪除]` 按鈕用 `bg-red-600`
- 主要按鈕 hover 0.3 秒才能點擊（防誤觸）

### 7.6 Inline 確認列（取代 modal）

非高風險動作（如 FAQ 刪除、版本還原），使用 inline 確認列。
成功後 Toast 顯示「已刪除 [↶ 復原（5s）]」按鈕，5 秒內可復原。

**樂觀刪除實作（純前端，不改後端）：**
1. 點擊「刪除」→ 前端立即從清單 hide（樂觀更新）
2. 啟動 5 秒倒數計時器
3. 計時內按下「復原」→ 取消計時、清單重新顯示
4. 計時結束 → 才真正送 `DELETE` API 請求
5. 若 API 失敗 → 清單恢復顯示 + Toast「刪除失敗」

### 7.7 焦點管理

| 場景 | 焦點規則 |
|------|---------|
| 開啟 Inline panel / dialog | 焦點移至第一個輸入框 |
| 關閉 dialog | 焦點返回觸發按鈕 |
| 表單提交失敗 | 焦點移至第一個錯誤欄位 |
| Toast 顯示 | 不搶焦點 |
| Empty state 行動按鈕 | 自動 focus |

### 7.8 無障礙

- 所有圖示按鈕必有 `aria-label`
- 所有圖片含 `alt`（裝飾用 `alt=""`）
- Color 不可為唯一狀態指示（status badge 同時有色 + 圖示 + 文字）
- 自訂元件 ARIA 屬性遵守 W3C 規範
- 跳過導覽連結 `Skip to main content`

---

## 8. shadcn/ui 元件清單

### 8.1 第一批：核心
```bash
npx shadcn@latest add button input label textarea card badge alert
npx shadcn@latest add dropdown-menu popover tooltip
npx shadcn@latest add sonner dialog alert-dialog
```

### 8.2 第二批：表單進階
```bash
npx shadcn@latest add form select combobox command
npx shadcn@latest add checkbox radio-group switch
```

### 8.3 第三批：列表與導覽
```bash
npx shadcn@latest add table breadcrumb tabs scroll-area separator
```

### 8.4 第四批:進階互動
```bash
npx shadcn@latest add resizable context-menu skeleton progress
```

### 8.5 自製元件

| 元件 | 基於 | 說明 |
|------|------|------|
| `Tree` | Radix Primitive | 類別樹（左欄） |
| `MarkdownEditor` | `@uiw/react-md-editor` | FAQ 答案編輯 |
| `TagInput` | `Input` + `Badge` | FAQ 標籤輸入 |
| `DiffViewer` | `react-diff-viewer-continued` | 版本比對 |
| `Dropzone` | `react-dropzone` | 檔案拖放 |
| `Kbd` | shadcn 樣式 + 自寫 | 鍵盤快捷鍵顯示 |

### 8.6 套件依賴

新增至 `package.json`：

```json
"dependencies": {
  "lucide-react": "^0.x",
  "sonner": "^1.x",
  "class-variance-authority": "^0.7.x",
  "clsx": "^2.x",
  "tailwind-merge": "^2.x",
  "@uiw/react-md-editor": "^4.x",
  "react-diff-viewer-continued": "^3.x",
  "react-dropzone": "^14.x"
},
"devDependencies": {
  "msw": "^2.x"
}
```

---

## 9. 檔案結構

```
frontend/src/
├── App.tsx                          # 路由配置 + 全域 Providers
├── main.tsx
├── index.css                        # tailwind base + design tokens
├── test-setup.ts
│
├── components/ui/                   # shadcn 元件
│
├── components/                       # 跨 feature 共用元件
│   ├── AppShell.tsx
│   ├── Topbar.tsx
│   ├── Sidebar.tsx
│   ├── Breadcrumb.tsx
│   ├── EmptyState.tsx
│   ├── ErrorBoundary.tsx
│   ├── PageError.tsx
│   ├── KeyboardShortcuts.tsx
│   └── Kbd.tsx
│
├── features/
│   ├── auth/
│   ├── agents/
│   ├── dashboard/
│   ├── knowledge/                   # 三欄主畫面
│   ├── sync/
│   ├── import-export/
│   ├── audit/
│   ├── chat/
│   └── users/
│
├── api/
│   ├── client.ts
│   ├── types.ts
│   └── endpoints/                   # 按 feature 拆分
│
├── store/                           # Zustand
│   ├── useAuthStore.ts
│   ├── useAgentContext.ts
│   └── useUiPreferences.ts
│
├── lib/
│   ├── utils.ts
│   ├── categories.ts
│   ├── diff.ts
│   ├── format.ts
│   ├── keyboard.ts
│   └── constants.ts
│
├── hooks/
│   ├── useDebounce.ts
│   ├── useLocalStorage.ts
│   ├── useKeyboardShortcut.ts
│   ├── useResizable.ts
│   └── useAutoSave.ts
│
├── routes/
│   ├── ProtectedRoute.tsx
│   └── AdminRoute.tsx
│
└── mocks/                           # MSW
    ├── handlers.ts
    └── server.ts
```

**Clean code 強制：**
- 每個 `.tsx` ≤ 150 行，超過必拆
- 每個 component / hook / util 配套 `.test.tsx` 或 `.test.ts`
- `pages/` 目錄完全廢除（已併入 `features/<name>/<Name>Page.tsx`）

---

## 10. 廢除清單

| 廢除項目 | 原因 | 取代 |
|---------|------|------|
| `frontend/src/pages/CreateAgentModal.tsx` | 違反「不開新視窗」 | `features/agents/CreateAgentInlinePanel.tsx` |
| `frontend/src/pages/Categories.tsx` 整頁 | 併入 KnowledgeBase 三欄左側 | `features/knowledge/CategoryTree.tsx` |
| `frontend/src/pages/` 整個目錄 | 改 feature-based 結構 | `features/<name>/<Name>Page.tsx` |
| `index.css` 中 `.btn-*` `.badge-*` `.card` `.input` | 改用 shadcn 元件 | shadcn `Button` `Badge` `Card` `Input` |
| `useDialogStore` 中 `showPrompt()` | 違反「不開新視窗」 | inline edit 取代 |
| 所有 emoji 圖示 | pro-max 規則 | Lucide React |
| 路由 `/agents/:id/categories` | 併入 knowledge | （刪除路由） |

---

## 11. 測試策略（F.I.R.S.T.）

### 11.1 三層測試金字塔

| 層級 | 工具 | 涵蓋率目標 |
|------|------|----------|
| Unit | Vitest | 純函式 100% / hook 90% |
| Component | Vitest + RTL | 互動關鍵元件 80% |
| Integration | Vitest + MSW | feature 主流程 70% |

### 11.2 強制測試清單（P0 元件）

| 元件 / Hook | 必測情境 |
|------------|---------|
| `useFaqList` | 篩選、分頁、搜尋、URL 同步 |
| `useCategoryTree` | 新增、改名、刪除、收合狀態 |
| `useAutoSave` | debounce、樂觀更新、失敗回滾 |
| `useFaqSelection` | 多選、shift 範圍選 |
| `CategoryTree` | 雙擊改名、hover 出 menu |
| `FaqDetail` | inline 編輯、Esc 取消、Cmd+Enter 儲存 |
| `VersionDiffView` | diff 計算、rollback 流程 |
| `lib/categories.ts` | flat → tree 轉換 |
| `lib/diff.ts` | 各種變更場景 |

### 11.3 MSW 設定

- `mocks/handlers.ts` 定義所有 API mock
- `test-setup.ts` 自動啟動 server
- 取代現有 axios mock

### 11.4 CI 規則

PR 必過：
- `tsc --noEmit`
- `eslint`
- `vitest run`
- coverage ≥ 70%

---

## 12. 漸進式落地計畫

避免一次砍掉重練、保留可運作狀態：

| Phase | 範圍 | 可運作性 |
|-------|------|---------|
| **P1** | 安裝 shadcn + tokens + 全站 layout（AppShell / Topbar / Sidebar / Breadcrumb） | ✅ |
| **P2** | Login + AgentSelect + CreateAgentInlinePanel | ✅ |
| **P3** | KnowledgeBase 三欄主畫面 + FaqDetail + 版本歷史（核心、最大） | ✅ |
| **P4** | Dashboard + SyncPage 歷史 + 後端新增 sync/history endpoint | ✅ |
| **P5** | ImportExport + AuditLog + UserManagement + AgentSettings + TestChat | ✅ |
| **P6** | 廢除舊檔（CreateAgentModal、Categories、舊 useDialogStore.showPrompt）+ index.css 清理 | ✅ |
| **P7** | Polish（鍵盤快捷鍵速查表、reduced-motion、a11y 檢查、Lighthouse） | ✅ |

---

## 13. 後端配合事項

共三個新端點：

### 13.1 `GET /api/v1/agents/:id/sync/history`
- 回傳該 Agent 最近 20 筆 SyncLog（依 `started_at DESC`）
- 包含完整 stdout、stderr、duration_sec、items_count
- 權限：reviewer / superadmin
- 用於：SyncPage §6.4 歷史紀錄 timeline

### 13.2 `POST /api/v1/agents/:id/test-connection`
- 後端代為對 Agent 的 `rasa_rest_url` 送 GET request 並回傳 status / latency
- 避免前端直接呼叫造成 CORS 問題
- 權限：superadmin
- 用於：AgentSettings §6.8「測試連線」按鈕

### 13.3 `POST /api/v1/agents/:id/validate-script`
- 後端在 celery_worker 容器內檢查 `agent.ingest_script_path` 對應的檔案是否存在 + 可執行
- 回傳 `{ exists: bool, executable: bool, size_bytes: int }`
- 權限：superadmin
- 用於：AgentSettings §6.8「驗證腳本存在性」按鈕

其餘前端改造**不需**任何後端 API 變更。

---

## 14. 驗收標準

### 14.1 功能驗收
- [ ] 所有 P0 / P1 問題已解決（見第 1.1 設計目標）
- [ ] 三欄式 KnowledgeBase 完整可用（樹編輯、列表篩選、詳情 inline 編輯、版本比對與還原）
- [ ] 所有「新增」「編輯」操作不開 modal（除白名單 5 場景）
- [ ] 鍵盤可達成所有核心操作

### 14.2 技術驗收
- [ ] TypeScript `tsc --noEmit` 零錯誤
- [ ] ESLint 零警告
- [ ] Vitest coverage ≥ 70%
- [ ] 每個 `.tsx` ≤ 150 行
- [ ] `pages/` 目錄完全清空
- [ ] `index.css` 中無手刻 `.btn-*` `.badge-*` `.card` `.input`

### 14.3 視覺驗收
- [ ] 全站無 emoji 當圖示
- [ ] 焦點環視覺可見
- [ ] 對比度 ≥ 4.5:1（WCAG AA）
- [ ] 1280px / 1024px 兩斷點視覺正確
- [ ] `prefers-reduced-motion` 啟用時動畫關閉

### 14.4 互動驗收
- [ ] 所有清單頁顯示 skeleton（無「載入中...」純文字）
- [ ] Empty state 含引導行動（無「無資料」純文字）
- [ ] Toast 同類訊息合併
- [ ] 所有清單支援 URL filter 同步

---

## 15. 風險與決策

### 15.1 已知風險

| 風險 | 影響 | 緩解 |
|------|------|------|
| shadcn 元件版本與 Tailwind 衝突 | 安裝失敗 | 鎖定 Tailwind 3.x 主版本，shadcn 用對應 CLI 版本 |
| Markdown 編輯器 bundle 過大 | 首次載入慢 | dynamic import / route-based code splitting |
| 三欄 RWD 在 1280–1440 邊界 layout 抖動 | 視覺不穩 | 明確 breakpoint + 過渡動畫 |
| 漸進落地中舊新並存 | 短期不一致 | Phase 順序設計使每階段可獨立部署 |

### 15.2 重要決策紀錄

1. **不採用 pro-max 推薦的 Fira Code 當 heading**：與 B Notion 風格衝突，改用 Inter（shadcn 預設）
2. **不交付 dark mode**：token 預備但 Phase 1 不做（YAGNI）
3. **不主推 mobile**：< 1024px 顯示警告（內部工具）
4. **拖曳節點重排父子關係延後**：Phase 2 nice-to-have
5. **取消「輸入名稱確認」刪除驗證**：簡化版用紅色按鈕 + 防誤觸延遲

---

## 16. 文件版本

| 版本 | 日期 | 變更 |
|------|------|------|
| v1.0 | 2026-04-30 | 初版（含全部 6 節設計，使用者已逐節核可） |
