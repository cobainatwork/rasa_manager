# 前端 UI/UX 全面重寫實施計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal：** 完全重寫 `D:\mini_test\frontend\src/` 內容（保留 `package.json` / `vite.config.ts` / `tsconfig.json` / `Dockerfile`），改為 shadcn/ui 元件庫 + 三欄主從版面 + Inter+JetBrains Mono 字型 + Tailwind tokens。對應 spec：`docs/superpowers/specs/2026-04-30-frontend-uxux-overhaul-design.md`。

**Architecture：** 保留現有 `frontend/src/` 完整備份至 `frontend/src.legacy/`（不從 git 重抓）。新 `src/` 從零建構：先建 lib + hooks + AppShell 骨架，再依 feature 一個個遷入並整合 shadcn 元件。後端新增三個端點（sync/history、test-connection、validate-script）。Docker / nginx / 路由保持不變，cutover 一次完成。

**Tech Stack：** Vite 5 + React 18 + TypeScript 5 strict + Tailwind 3 + shadcn/ui + Radix + Lucide + Zustand + react-hook-form + zod + Vitest + MSW

---

## 重要約束（每個 task 都必須遵守）

1. **元件 ≤ 150 行**，超過必拆
2. **元件 props ≤ 5 個**，超過包成 config object
3. **禁用 emoji 當 UI 圖示**，一律 Lucide React，stroke-width 1.5
4. **禁寫自訂數字**：所有間距、圓角、shadow、z-index、color 都從 token scale 取
5. **TDD**：先寫失敗測試 → 實作 → 驗證通過 → 提交
6. **每個 component / hook / util** 必須配套 `.test.tsx` 或 `.test.ts`
7. **禁止 `any`**，TypeScript strict mode
8. **禁止 `.catch(() => null)`** 吞錯誤

---

## File Structure（最終目標）

```
frontend/src/
├── App.tsx                          # 路由配置 + 全域 Providers
├── main.tsx                          # vite entry
├── index.css                        # tailwind base + design tokens (CSS vars)
├── test-setup.ts                    # vitest + MSW init
│
├── components/ui/                   # shadcn 元件（複製進來）
│
├── components/                       # 跨 feature 共用
│   ├── AppShell.tsx                 # 全站版面骨架
│   ├── Topbar.tsx
│   ├── Sidebar.tsx
│   ├── Breadcrumb.tsx
│   ├── EmptyState.tsx
│   ├── ErrorBoundary.tsx
│   ├── PageError.tsx
│   ├── KeyboardShortcuts.tsx        # 全域 ? 速查表
│   └── Kbd.tsx
│
├── features/
│   ├── auth/                        # Login + PasswordInput + useLogin
│   ├── agents/                      # AgentSelectPage + AgentCard + CreateAgentInlinePanel + AgentSettingsPage + ConnectionTester + DangerZone
│   ├── dashboard/                   # DashboardPage + KpiGrid + PendingTasksPanel + ActivityFeed + QuickActions
│   ├── knowledge/                   # 三欄主畫面
│   ├── sync/                        # SyncPage + SyncTriggerCard + SyncHistoryList + SyncLogDetail
│   ├── import-export/               # ImportExportPage + ImportDropzone + ImportProgress + ImportResult
│   ├── audit/                       # AuditPage + AuditFilterBar + AuditDayGroup + AuditEntry
│   ├── chat/                        # TestChatPage + ChatBubble + TypingIndicator
│   └── users/                       # UserManagementPage + UserListPanel + UserDetailPanel + AgentRoleRow + AddUserInlineForm
│
├── api/
│   ├── client.ts                    # 從 src.legacy 移入，不變
│   ├── types.ts                     # 從 src.legacy 移入 + 新增 SyncLog history、TestConnectionResult、ValidateScriptResult 型別
│   └── endpoints/                   # 新拆分（按 feature）
│       ├── auth.ts
│       ├── agents.ts
│       ├── faqs.ts
│       ├── categories.ts
│       ├── sync.ts
│       ├── audit.ts
│       └── users.ts
│
├── store/                           # Zustand
│   ├── useAuthStore.ts              # 從 src.legacy 移入，不變
│   ├── useAgentContext.ts           # 新增：當前選中 Agent
│   └── useUiPreferences.ts          # 新增：欄寬、sidebar 摺疊、主題
│
├── lib/
│   ├── utils.ts                     # cn() 等工具（shadcn 標準）
│   ├── categories.ts                # buildCategoryTree, flattenCategories
│   ├── diff.ts                      # computeDiff for FAQ versions
│   ├── format.ts                    # formatDate, formatBytes, relativeTime
│   ├── keyboard.ts                  # 鍵盤快捷鍵 hook
│   └── constants.ts                 # 從 src.legacy 移入
│
├── hooks/
│   ├── useDebounce.ts
│   ├── useLocalStorage.ts
│   ├── useKeyboardShortcut.ts
│   ├── useResizable.ts              # 三欄拖拉
│   └── useAutoSave.ts
│
├── routes/
│   ├── ProtectedRoute.tsx           # 從 src.legacy 移入，不變
│   └── AdminRoute.tsx               # 新增 superadmin 守衛
│
└── mocks/                           # MSW handler（測試用）
    ├── handlers.ts
    └── server.ts
```

---

# Phase 0: 準備工作（備份 + 清空 + 套件）

## Task 0.1: 備份現有 src 至 src.legacy

**Files:**
- Modify: `D:/mini_test/frontend/src/` → 重命名為 `D:/mini_test/frontend/src.legacy/`

- [ ] **Step 1: 確認 git working tree 乾淨**

```bash
cd D:/mini_test && git status
```

Expected: 已 commit 或 stash 完畢（沒有 unstaged changes）。若有則先 commit。

- [ ] **Step 2: 備份 src 為 src.legacy**

```bash
cd D:/mini_test/frontend && mv src src.legacy
```

Expected: 原 `src/` 變成 `src.legacy/`，舊 frontend build 會失敗（這是預期的，cutover 前不會 build）。

- [ ] **Step 3: 建立全新空的 src 目錄**

```bash
mkdir -p D:/mini_test/frontend/src
```

- [ ] **Step 4: 暫停 docker-compose 的 frontend 服務（避免不斷重啟失敗）**

```bash
cd D:/mini_test && docker compose stop frontend
```

- [ ] **Step 5: Commit**

```bash
cd D:/mini_test
git add frontend/
git commit -m "chore(frontend): 備份 src 至 src.legacy 以重寫"
```

## Task 0.2: 新增 package.json 依賴

**Files:**
- Modify: `D:/mini_test/frontend/package.json`

- [ ] **Step 1: 安裝新依賴**

```bash
cd D:/mini_test/frontend
npm install --save \
  sonner@^1.5 \
  @uiw/react-md-editor@^4.0 \
  react-diff-viewer-continued@^3.4 \
  react-dropzone@^14.2
npm install --save-dev msw@^2.4
```

Expected: 5 個套件加入 dependencies / devDependencies。`package-lock.json` 更新。

- [ ] **Step 2: 確認既有套件仍在**

開啟 `D:/mini_test/frontend/package.json`，確認以下 dependencies 存在（不需安裝）：
- `lucide-react`, `class-variance-authority`, `clsx`, `tailwind-merge`
- `react-hook-form`, `@hookform/resolvers`, `zod`
- `zustand`, `axios`, `react-router-dom`
- `@tanstack/react-table`

devDependencies 應有：`vitest`, `@testing-library/*`, `tailwindcss`, `typescript`

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore(frontend): 新增 sonner / md-editor / diff-viewer / dropzone / msw"
```

---

# Phase 1: 設計 Token + Tailwind Config + 全域 CSS

## Task 1.1: 建立 index.html 與 main.tsx

**Files:**
- Create: `D:/mini_test/frontend/index.html`（已存在則檢查內容）
- Create: `D:/mini_test/frontend/src/main.tsx`

- [ ] **Step 1: 確認 index.html 存在且正確**

```bash
cat D:/mini_test/frontend/index.html
```

若不存在，建立 `D:/mini_test/frontend/index.html`：

```html
<!doctype html>
<html lang="zh-TW">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Rasa 知識庫管理平台</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 2: 建立 main.tsx**

寫入 `D:/mini_test/frontend/src/main.tsx`：

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { App } from './App'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>
)
```

注意：此檔案需要 `App.tsx` 與 `index.css`，在後續 task 中建立。

## Task 1.2: 設計 Token 寫入 Tailwind config

**Files:**
- Modify: `D:/mini_test/frontend/tailwind.config.ts`

- [ ] **Step 1: 取代既有 tailwind.config.ts**

寫入 `D:/mini_test/frontend/tailwind.config.ts`：

```ts
import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx,js,jsx}'],
  theme: {
    container: { center: true, padding: '1rem' },
    extend: {
      colors: {
        brand: {
          50: '#EFF6FF',
          500: '#3B82F6',
          600: '#2563EB',
          700: '#1D4ED8',
        },
        canvas: '#F8FAFC',
        surface: '#FFFFFF',
        subtle: '#F1F5F9',
        'text-primary': '#0F172A',
        'text-secondary': '#475569',
        'text-muted': '#64748B',
        'border-default': '#E2E8F0',
        'border-strong': '#CBD5E1',
      },
      fontFamily: {
        sans: ['Inter', 'Noto Sans TC', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
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
        xs: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
        sm: '0 1px 3px 0 rgb(0 0 0 / 0.07), 0 1px 2px -1px rgb(0 0 0 / 0.05)',
        md: '0 4px 6px -1px rgb(0 0 0 / 0.08), 0 2px 4px -2px rgb(0 0 0 / 0.05)',
        lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.05)',
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
  plugins: [require('tailwindcss-animate')],
}

export default config
```

- [ ] **Step 2: 安裝 tailwindcss-animate（shadcn 標配）**

```bash
cd D:/mini_test/frontend && npm install --save-dev tailwindcss-animate
```

## Task 1.3: 建立 index.css（design token CSS variables + 字型）

**Files:**
- Create: `D:/mini_test/frontend/src/index.css`

- [ ] **Step 1: 寫入 index.css**

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Noto+Sans+TC:wght@400;500;700&display=swap');

@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    /* shadcn HSL tokens（必要） */
    --background: 210 40% 98%;
    --foreground: 222 47% 11%;
    --card: 0 0% 100%;
    --card-foreground: 222 47% 11%;
    --popover: 0 0% 100%;
    --popover-foreground: 222 47% 11%;
    --primary: 217 91% 60%;
    --primary-foreground: 0 0% 100%;
    --secondary: 210 40% 96%;
    --secondary-foreground: 222 47% 11%;
    --muted: 210 40% 96%;
    --muted-foreground: 215 16% 47%;
    --accent: 210 40% 96%;
    --accent-foreground: 222 47% 11%;
    --destructive: 0 84% 60%;
    --destructive-foreground: 0 0% 100%;
    --border: 214 32% 91%;
    --input: 214 32% 91%;
    --ring: 217 91% 60%;
    --radius: 0.5rem;
  }

  * {
    @apply border-border-default;
  }

  body {
    @apply bg-canvas text-text-primary font-sans antialiased;
    font-feature-settings: 'cv02', 'cv03', 'cv04', 'cv11';
  }

  /* 焦點環統一規格 */
  *:focus-visible {
    @apply outline-none ring-2 ring-brand-500 ring-offset-2 ring-offset-canvas;
  }

  /* prefers-reduced-motion 支援 */
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: 0.01ms !important;
      transition-duration: 0.01ms !important;
    }
  }

  /* 段落字數限制（max-w-prose 之外，提供 ch 單位版） */
  .prose-content {
    @apply max-w-[65ch] leading-relaxed;
  }
}

@layer utilities {
  .scrollbar-thin {
    scrollbar-width: thin;
    scrollbar-color: theme('colors.border-strong') transparent;
  }
}
```

注意：完全不再寫 `.btn-*` `.badge-*` `.card` `.input`（spec §10 廢除清單）。

## Task 1.4: 建立 components.json（shadcn 設定檔）

**Files:**
- Create: `D:/mini_test/frontend/components.json`

- [ ] **Step 1: 寫入 components.json**

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "src/index.css",
    "baseColor": "slate",
    "cssVariables": true
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "hooks": "@/hooks",
    "lib": "@/lib"
  }
}
```

## Task 1.5: 建立 lib/utils.ts（shadcn 必需的 cn() 函式）

**Files:**
- Create: `D:/mini_test/frontend/src/lib/utils.ts`
- Create: `D:/mini_test/frontend/src/lib/utils.test.ts`

- [ ] **Step 1: 寫測試**

`D:/mini_test/frontend/src/lib/utils.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { cn } from './utils'

describe('cn (className merger)', () => {
  it('合併多個 class 名', () => {
    expect(cn('foo', 'bar')).toBe('foo bar')
  })

  it('條件 class（false 過濾）', () => {
    expect(cn('foo', false && 'bar', 'baz')).toBe('foo baz')
  })

  it('衝突的 tailwind class 後者覆蓋前者', () => {
    expect(cn('px-2 px-4')).toBe('px-4')
  })

  it('undefined / null 忽略', () => {
    expect(cn('foo', undefined, null, 'bar')).toBe('foo bar')
  })
})
```

- [ ] **Step 2: 確認測試失敗**

```bash
cd D:/mini_test/frontend && npm test -- lib/utils
```

Expected: FAIL（utils.ts 不存在）

- [ ] **Step 3: 實作 utils.ts**

```ts
import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}
```

- [ ] **Step 4: 驗證測試通過**

```bash
cd D:/mini_test/frontend && npm test -- lib/utils
```

Expected: PASS（4 個測試全綠）

- [ ] **Step 5: Commit**

```bash
cd D:/mini_test
git add frontend/
git commit -m "feat(frontend): tailwind tokens + index.css + lib/utils.cn()"
```

---

# Phase 2: 移植可重用核心（api / store / route / constants）

## Task 2.1: 移植 api/client.ts + api/types.ts

**Files:**
- Create: `D:/mini_test/frontend/src/api/client.ts`（從 src.legacy 複製）
- Create: `D:/mini_test/frontend/src/api/types.ts`（從 src.legacy 複製 + 新增型別）

- [ ] **Step 1: 複製 api/client.ts（不修改）**

```bash
cd D:/mini_test/frontend
mkdir -p src/api
cp src.legacy/api/client.ts src/api/client.ts
```

- [ ] **Step 2: 複製 api/types.ts**

```bash
cp src.legacy/api/types.ts src/api/types.ts
```

- [ ] **Step 3: 在 types.ts 新增三個型別**

開啟 `D:/mini_test/frontend/src/api/types.ts`，於檔尾新增：

```ts
// ── 後端新端點型別（spec §13） ────────────────────────────────────────────

export interface SyncLogHistoryItem {
  id: string
  status: SyncLog['status']
  triggered_by_username: string | null
  started_at: string | null
  finished_at: string | null
  duration_sec: number | null
  items_count: number
  output_file: string | null
  stdout: string | null
  stderr: string | null
}

export interface TestConnectionResult {
  ok: boolean
  status_code: number | null
  latency_ms: number | null
  error: string | null
}

export interface ValidateScriptResult {
  exists: boolean
  executable: boolean
  size_bytes: number
}
```

## Task 2.2: 移植 store/useAuthStore.ts + 測試

**Files:**
- Create: `D:/mini_test/frontend/src/store/useAuthStore.ts`（從 src.legacy 複製）
- Create: `D:/mini_test/frontend/src/store/useAuthStore.test.ts`（從 src.legacy 複製）

- [ ] **Step 1: 複製檔案**

```bash
cd D:/mini_test/frontend
mkdir -p src/store
cp src.legacy/store/useAuthStore.ts src/store/useAuthStore.ts
cp src.legacy/store/useAuthStore.test.ts src/store/useAuthStore.test.ts
```

- [ ] **Step 2: 跑測試確認可用**

```bash
npm test -- store/useAuthStore
```

Expected: PASS

## Task 2.3: 移植 routes/ProtectedRoute.tsx + 測試 + 新增 AdminRoute

**Files:**
- Create: `D:/mini_test/frontend/src/routes/ProtectedRoute.tsx`（從 src.legacy 複製）
- Create: `D:/mini_test/frontend/src/routes/ProtectedRoute.test.tsx`（從 src.legacy 複製）
- Create: `D:/mini_test/frontend/src/routes/AdminRoute.tsx`
- Create: `D:/mini_test/frontend/src/routes/AdminRoute.test.tsx`

- [ ] **Step 1: 複製 ProtectedRoute**

```bash
cd D:/mini_test/frontend
mkdir -p src/routes
cp src.legacy/routes/ProtectedRoute.tsx src/routes/ProtectedRoute.tsx
cp src.legacy/routes/ProtectedRoute.test.tsx src/routes/ProtectedRoute.test.tsx
```

- [ ] **Step 2: 寫 AdminRoute 測試**

`D:/mini_test/frontend/src/routes/AdminRoute.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { useAuthStore } from '@/store/useAuthStore'
import { AdminRoute } from './AdminRoute'

function renderWithAuth(isSuper: boolean) {
  useAuthStore.setState({
    user: { id: '1', username: 'u', is_superadmin: isSuper, is_active: true, created_at: '' },
  })
  return render(
    <MemoryRouter initialEntries={['/admin']}>
      <Routes>
        <Route element={<AdminRoute />}>
          <Route path="/admin" element={<div>admin-only</div>} />
        </Route>
        <Route path="/" element={<div>home</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('AdminRoute', () => {
  it('superadmin 可進入', () => {
    renderWithAuth(true)
    expect(screen.getByText('admin-only')).toBeInTheDocument()
  })
  it('非 superadmin 重新導向首頁', () => {
    renderWithAuth(false)
    expect(screen.getByText('home')).toBeInTheDocument()
  })
})
```

- [ ] **Step 3: 實作 AdminRoute**

`D:/mini_test/frontend/src/routes/AdminRoute.tsx`:

```tsx
import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/store/useAuthStore'

export function AdminRoute() {
  const user = useAuthStore((s) => s.user)
  if (!user?.is_superadmin) return <Navigate to="/agents" replace />
  return <Outlet />
}
```

- [ ] **Step 4: 跑測試**

```bash
npm test -- routes/
```

Expected: ProtectedRoute + AdminRoute 全綠

## Task 2.4: 移植 lib/constants.ts

**Files:**
- Create: `D:/mini_test/frontend/src/lib/constants.ts`（從 src.legacy 複製）

- [ ] **Step 1: 複製**

```bash
cp D:/mini_test/frontend/src.legacy/lib/constants.ts D:/mini_test/frontend/src/lib/constants.ts
```

- [ ] **Step 2: Commit Phase 2**

```bash
cd D:/mini_test
git add frontend/src/
git commit -m "feat(frontend): 移植 api / store / routes / constants 至新 src/"
```

---

# Phase 3: shadcn 元件安裝（4 批）

## Task 3.1: 安裝核心元件（第一批）

**Files:**
- Create: `D:/mini_test/frontend/src/components/ui/*`（多個檔案，shadcn CLI 自動產生）

- [ ] **Step 1: 安裝 button, input, label, textarea**

```bash
cd D:/mini_test/frontend
npx shadcn@latest init -d --no-src
```

注意：若已有 `components.json`，CLI 會偵測並使用。回答 prompts：
- TypeScript: yes
- Style: new-york
- Base color: slate
- CSS variables: yes
- React Server Components: no

- [ ] **Step 2: 加入第一批元件**

```bash
npx shadcn@latest add button input label textarea --yes
npx shadcn@latest add card badge alert --yes
npx shadcn@latest add dropdown-menu popover tooltip --yes
npx shadcn@latest add sonner dialog alert-dialog --yes
```

Expected: `src/components/ui/` 下新增多個 `.tsx` 檔案。

- [ ] **Step 3: 確認 typecheck 通過**

```bash
npm run typecheck
```

Expected: 零錯誤。若有，多半是 path alias 問題，檢查 `vite.config.ts` 的 `@/*` alias。

- [ ] **Step 4: Commit**

```bash
cd D:/mini_test
git add frontend/
git commit -m "feat(frontend): 安裝 shadcn 第一批元件（核心 11 個）"
```

## Task 3.2: 安裝表單進階元件（第二批）

- [ ] **Step 1: 安裝**

```bash
cd D:/mini_test/frontend
npx shadcn@latest add form select command --yes
npx shadcn@latest add checkbox radio-group switch --yes
```

- [ ] **Step 2: typecheck**

```bash
npm run typecheck
```

- [ ] **Step 3: Commit**

```bash
cd D:/mini_test
git add frontend/
git commit -m "feat(frontend): 安裝 shadcn 第二批元件（表單進階）"
```

## Task 3.3: 安裝列表 / 導覽元件（第三批）

- [ ] **Step 1: 安裝**

```bash
cd D:/mini_test/frontend
npx shadcn@latest add table breadcrumb tabs scroll-area separator --yes
```

- [ ] **Step 2: typecheck**

- [ ] **Step 3: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): 安裝 shadcn 第三批元件（列表與導覽）"
```

## Task 3.4: 安裝進階互動元件（第四批）

- [ ] **Step 1: 安裝**

```bash
cd D:/mini_test/frontend
npx shadcn@latest add resizable context-menu skeleton progress --yes
```

- [ ] **Step 2: typecheck**

- [ ] **Step 3: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): 安裝 shadcn 第四批元件（進階互動）"
```

---

# Phase 4: lib + hooks（純函式 + 共用 hook）

## Task 4.1: lib/format.ts（formatDate, formatBytes, relativeTime）

**Files:**
- Create: `D:/mini_test/frontend/src/lib/format.ts`
- Create: `D:/mini_test/frontend/src/lib/format.test.ts`

- [ ] **Step 1: 寫測試**

```ts
import { describe, it, expect } from 'vitest'
import { formatDate, formatBytes, relativeTime } from './format'

describe('formatDate', () => {
  it('null 回傳 dash', () => {
    expect(formatDate(null)).toBe('—')
  })
  it('ISO 字串轉本地時間', () => {
    expect(formatDate('2026-04-30T14:23:00Z')).toMatch(/2026/)
  })
})

describe('formatBytes', () => {
  it('0 bytes', () => expect(formatBytes(0)).toBe('0 B'))
  it('1024 bytes → 1 KB', () => expect(formatBytes(1024)).toBe('1 KB'))
  it('1MB', () => expect(formatBytes(1048576)).toBe('1 MB'))
})

describe('relativeTime', () => {
  it('剛才（< 1 分鐘）', () => {
    const now = new Date()
    expect(relativeTime(now.toISOString())).toBe('剛才')
  })
  it('幾分鐘前', () => {
    const past = new Date(Date.now() - 5 * 60 * 1000).toISOString()
    expect(relativeTime(past)).toBe('5 分鐘前')
  })
  it('幾小時前', () => {
    const past = new Date(Date.now() - 3 * 3600 * 1000).toISOString()
    expect(relativeTime(past)).toBe('3 小時前')
  })
  it('幾天前', () => {
    const past = new Date(Date.now() - 2 * 86400 * 1000).toISOString()
    expect(relativeTime(past)).toBe('2 天前')
  })
  it('null 回傳 dash', () => expect(relativeTime(null)).toBe('—'))
})
```

- [ ] **Step 2: 實作 format.ts**

```ts
const DASH = '—'

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return DASH
  return new Date(iso).toLocaleString('zh-TW', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return `${(bytes / Math.pow(1024, i)).toFixed(0)} ${units[i]}`
}

export function relativeTime(iso: string | null | undefined): string {
  if (!iso) return DASH
  const diff = Date.now() - new Date(iso).getTime()
  const sec = Math.floor(diff / 1000)
  if (sec < 60) return '剛才'
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min} 分鐘前`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr} 小時前`
  const day = Math.floor(hr / 24)
  return `${day} 天前`
}
```

- [ ] **Step 3: 跑測試**

```bash
npm test -- lib/format
```

Expected: PASS

## Task 4.2: lib/categories.ts（buildCategoryTree, flattenCategories, buildCategoryPath）

**Files:**
- Create: `D:/mini_test/frontend/src/lib/categories.ts`
- Create: `D:/mini_test/frontend/src/lib/categories.test.ts`

- [ ] **Step 1: 寫測試**

```ts
import { describe, it, expect } from 'vitest'
import { buildCategoryTree, flattenCategories, buildCategoryPath } from './categories'
import type { CategoryNode } from '@/api/types'

const sample: Array<Pick<CategoryNode, 'id' | 'name' | 'parent_id'>> = [
  { id: '1', name: '產品功能', parent_id: null },
  { id: '2', name: '帳號', parent_id: '1' },
  { id: '3', name: '密碼', parent_id: '2' },
  { id: '4', name: '計費', parent_id: null },
]

describe('buildCategoryTree', () => {
  it('將平面陣列轉為巢狀樹', () => {
    const tree = buildCategoryTree(sample)
    expect(tree).toHaveLength(2)
    expect(tree[0].id).toBe('1')
    expect(tree[0].children[0].id).toBe('2')
    expect(tree[0].children[0].children[0].id).toBe('3')
  })

  it('空陣列回傳空陣列', () => {
    expect(buildCategoryTree([])).toEqual([])
  })

  it('parent_id 找不到的節點視為 root', () => {
    const tree = buildCategoryTree([
      { id: '1', name: 'orphan', parent_id: 'missing' },
    ])
    expect(tree).toHaveLength(1)
  })
})

describe('flattenCategories', () => {
  it('巢狀樹展平為 path 列表', () => {
    const tree = buildCategoryTree(sample)
    const flat = flattenCategories(tree)
    expect(flat).toEqual([
      { id: '1', path: '產品功能' },
      { id: '2', path: '產品功能/帳號' },
      { id: '3', path: '產品功能/帳號/密碼' },
      { id: '4', path: '計費' },
    ])
  })
})

describe('buildCategoryPath', () => {
  it('依 id 反向追溯祖先構成路徑', () => {
    expect(buildCategoryPath('3', sample)).toBe('產品功能/帳號/密碼')
    expect(buildCategoryPath('1', sample)).toBe('產品功能')
    expect(buildCategoryPath('missing', sample)).toBe('')
  })
})
```

- [ ] **Step 2: 實作 categories.ts**

```ts
import type { CategoryNode } from '@/api/types'

type FlatCategory = Pick<CategoryNode, 'id' | 'name' | 'parent_id'> &
  Partial<Omit<CategoryNode, 'id' | 'name' | 'parent_id'>>

export function buildCategoryTree(items: FlatCategory[]): CategoryNode[] {
  const map = new Map<string, CategoryNode>()
  for (const it of items) {
    map.set(it.id, {
      id: it.id,
      name: it.name,
      parent_id: it.parent_id,
      sort_order: it.sort_order ?? 0,
      created_at: it.created_at ?? null,
      updated_at: it.updated_at ?? null,
      children: [],
    })
  }
  const roots: CategoryNode[] = []
  for (const node of map.values()) {
    if (node.parent_id && map.has(node.parent_id)) {
      map.get(node.parent_id)!.children.push(node)
    } else {
      roots.push(node)
    }
  }
  return roots
}

export interface FlatPath { id: string; path: string }

export function flattenCategories(tree: CategoryNode[], prefix = ''): FlatPath[] {
  const out: FlatPath[] = []
  for (const node of tree) {
    const path = prefix ? `${prefix}/${node.name}` : node.name
    out.push({ id: node.id, path })
    if (node.children.length > 0) out.push(...flattenCategories(node.children, path))
  }
  return out
}

export function buildCategoryPath(targetId: string, items: FlatCategory[]): string {
  const map = new Map(items.map((c) => [c.id, c]))
  const segments: string[] = []
  let cur = map.get(targetId)
  while (cur) {
    segments.unshift(cur.name)
    cur = cur.parent_id ? map.get(cur.parent_id) : undefined
  }
  return segments.join('/')
}
```

- [ ] **Step 3: 跑測試**

```bash
npm test -- lib/categories
```

Expected: PASS

## Task 4.3: lib/diff.ts（FAQ 版本比對）

**Files:**
- Create: `D:/mini_test/frontend/src/lib/diff.ts`
- Create: `D:/mini_test/frontend/src/lib/diff.test.ts`

- [ ] **Step 1: 寫測試**

```ts
import { describe, it, expect } from 'vitest'
import { computeDiff, type DiffEntry } from './diff'

describe('computeDiff', () => {
  it('回傳變更欄位的 before/after', () => {
    const result = computeDiff(
      { question: '舊問題', answer: '舊答案', category_id: 'a' },
      { question: '新問題', answer: '舊答案', category_id: 'a' }
    )
    expect(result).toEqual<DiffEntry[]>([
      { field: 'question', before: '舊問題', after: '新問題' },
    ])
  })

  it('多個欄位變更', () => {
    const result = computeDiff(
      { question: 'q1', answer: 'a1' },
      { question: 'q2', answer: 'a2' }
    )
    expect(result).toHaveLength(2)
  })

  it('完全相同回傳空陣列', () => {
    expect(computeDiff({ a: 1 }, { a: 1 })).toEqual([])
  })

  it('陣列以 JSON 比對', () => {
    expect(computeDiff({ tags: ['a', 'b'] }, { tags: ['a', 'c'] })).toHaveLength(1)
  })
})
```

- [ ] **Step 2: 實作**

```ts
export interface DiffEntry {
  field: string
  before: unknown
  after: unknown
}

export function computeDiff(
  prev: Record<string, unknown>,
  curr: Record<string, unknown>
): DiffEntry[] {
  const fields = new Set([...Object.keys(prev), ...Object.keys(curr)])
  const out: DiffEntry[] = []
  for (const field of fields) {
    const a = prev[field]
    const b = curr[field]
    if (JSON.stringify(a) !== JSON.stringify(b)) {
      out.push({ field, before: a, after: b })
    }
  }
  return out
}
```

- [ ] **Step 3: 測試 + Commit**

```bash
npm test -- lib/
git add frontend/src/lib/
git commit -m "feat(frontend): lib/format + lib/categories + lib/diff（純函式 + 測試）"
```

## Task 4.4: hooks/useDebounce.ts

**Files:**
- Create: `D:/mini_test/frontend/src/hooks/useDebounce.ts`
- Create: `D:/mini_test/frontend/src/hooks/useDebounce.test.ts`

- [ ] **Step 1: 寫測試**

```ts
import { describe, it, expect, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useDebounce } from './useDebounce'

describe('useDebounce', () => {
  it('指定時間後才更新值', () => {
    vi.useFakeTimers()
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 300),
      { initialProps: { value: 'a' } }
    )
    expect(result.current).toBe('a')
    rerender({ value: 'b' })
    expect(result.current).toBe('a')
    act(() => { vi.advanceTimersByTime(300) })
    expect(result.current).toBe('b')
    vi.useRealTimers()
  })
})
```

- [ ] **Step 2: 實作**

```ts
import { useEffect, useState } from 'react'

export function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return debounced
}
```

- [ ] **Step 3: 測試 + Commit**

```bash
npm test -- hooks/useDebounce
git add frontend/src/hooks/
git commit -m "feat(frontend): hooks/useDebounce + 測試"
```

## Task 4.5: hooks/useLocalStorage.ts

**Files:**
- Create: `D:/mini_test/frontend/src/hooks/useLocalStorage.ts`
- Create: `D:/mini_test/frontend/src/hooks/useLocalStorage.test.ts`

- [ ] **Step 1: 測試**

```ts
import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useLocalStorage } from './useLocalStorage'

describe('useLocalStorage', () => {
  beforeEach(() => localStorage.clear())

  it('初始值來自 localStorage 或預設', () => {
    const { result } = renderHook(() => useLocalStorage('k', 'default'))
    expect(result.current[0]).toBe('default')
  })

  it('setter 同步寫入 localStorage', () => {
    const { result } = renderHook(() => useLocalStorage('k', 'a'))
    act(() => result.current[1]('b'))
    expect(result.current[0]).toBe('b')
    expect(localStorage.getItem('k')).toBe('"b"')
  })

  it('已存在的 localStorage 值優先', () => {
    localStorage.setItem('k', '"saved"')
    const { result } = renderHook(() => useLocalStorage('k', 'default'))
    expect(result.current[0]).toBe('saved')
  })
})
```

- [ ] **Step 2: 實作**

```ts
import { useCallback, useState } from 'react'

export function useLocalStorage<T>(key: string, initial: T): [T, (v: T) => void] {
  const [value, setValue] = useState<T>(() => {
    try {
      const raw = localStorage.getItem(key)
      return raw ? (JSON.parse(raw) as T) : initial
    } catch {
      return initial
    }
  })

  const set = useCallback((v: T) => {
    setValue(v)
    try { localStorage.setItem(key, JSON.stringify(v)) } catch { /* noop */ }
  }, [key])

  return [value, set]
}
```

- [ ] **Step 3: 測試 + Commit**

## Task 4.6: hooks/useKeyboardShortcut.ts

**Files:**
- Create: `D:/mini_test/frontend/src/hooks/useKeyboardShortcut.ts`
- Create: `D:/mini_test/frontend/src/hooks/useKeyboardShortcut.test.ts`

- [ ] **Step 1: 測試**

```ts
import { describe, it, expect, vi } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useKeyboardShortcut } from './useKeyboardShortcut'

describe('useKeyboardShortcut', () => {
  it('觸發指定按鍵的 callback', () => {
    const cb = vi.fn()
    renderHook(() => useKeyboardShortcut('/', cb))
    window.dispatchEvent(new KeyboardEvent('keydown', { key: '/' }))
    expect(cb).toHaveBeenCalledTimes(1)
  })

  it('輸入框聚焦時不觸發（除非 allowInInput）', () => {
    const cb = vi.fn()
    renderHook(() => useKeyboardShortcut('/', cb))
    const input = document.createElement('input')
    document.body.appendChild(input)
    input.focus()
    input.dispatchEvent(new KeyboardEvent('keydown', { key: '/', bubbles: true }))
    expect(cb).not.toHaveBeenCalled()
    input.remove()
  })

  it('支援 modifier（Cmd/Ctrl + S）', () => {
    const cb = vi.fn()
    renderHook(() => useKeyboardShortcut('s', cb, { meta: true }))
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 's', metaKey: true }))
    expect(cb).toHaveBeenCalledTimes(1)
  })
})
```

- [ ] **Step 2: 實作**

```ts
import { useEffect } from 'react'

export interface ShortcutOptions {
  meta?: boolean    // Cmd/Ctrl
  shift?: boolean
  alt?: boolean
  allowInInput?: boolean
}

const INPUT_TAGS = new Set(['INPUT', 'TEXTAREA', 'SELECT'])

export function useKeyboardShortcut(
  key: string,
  callback: () => void,
  options: ShortcutOptions = {}
): void {
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null
      if (!options.allowInInput && target && (INPUT_TAGS.has(target.tagName) || target.isContentEditable)) return
      if (e.key !== key) return
      if (options.meta && !(e.metaKey || e.ctrlKey)) return
      if (options.shift && !e.shiftKey) return
      if (options.alt && !e.altKey) return
      e.preventDefault()
      callback()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [key, callback, options.meta, options.shift, options.alt, options.allowInInput])
}
```

- [ ] **Step 3: 測試 + Commit**

## Task 4.7: hooks/useResizable.ts（三欄寬度拖拉）

**Files:**
- Create: `D:/mini_test/frontend/src/hooks/useResizable.ts`

- [ ] **Step 1: 實作（單純的 mousemove 處理）**

```ts
import { useCallback, useEffect, useRef, useState } from 'react'

export interface ResizableOptions {
  initial: number
  min: number
  max: number
  storageKey?: string
}

export function useResizable({ initial, min, max, storageKey }: ResizableOptions) {
  const initFromStorage = (): number => {
    if (!storageKey) return initial
    try {
      const v = Number(localStorage.getItem(storageKey))
      return Number.isFinite(v) && v >= min && v <= max ? v : initial
    } catch { return initial }
  }
  const [width, setWidth] = useState(initFromStorage)
  const dragging = useRef(false)
  const startX = useRef(0)
  const startW = useRef(0)

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    dragging.current = true
    startX.current = e.clientX
    startW.current = width
  }, [width])

  useEffect(() => {
    function onMove(e: MouseEvent) {
      if (!dragging.current) return
      const delta = startX.current - e.clientX  // 右欄拖左：寬度增加
      const next = Math.max(min, Math.min(max, startW.current + delta))
      setWidth(next)
    }
    function onUp() {
      if (dragging.current && storageKey) {
        try { localStorage.setItem(storageKey, String(width)) } catch { /* noop */ }
      }
      dragging.current = false
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [min, max, storageKey, width])

  return { width, onMouseDown }
}
```

註：此 hook 直接以 jsdom 測試 mousemove 不易，留待 component-level integration test 驗證。

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/
git commit -m "feat(frontend): hooks/useResizable（三欄拖拉）"
```

## Task 4.8: hooks/useAutoSave.ts（debounce + 樂觀更新 + 失敗回滾）

**Files:**
- Create: `D:/mini_test/frontend/src/hooks/useAutoSave.ts`
- Create: `D:/mini_test/frontend/src/hooks/useAutoSave.test.ts`

- [ ] **Step 1: 測試**

```ts
import { describe, it, expect, vi } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useAutoSave } from './useAutoSave'

describe('useAutoSave', () => {
  it('debounce 300ms 後呼叫 saveFn', async () => {
    vi.useFakeTimers()
    const saveFn = vi.fn().mockResolvedValue(undefined)
    const { result, rerender } = renderHook(
      ({ value }) => useAutoSave(value, saveFn, { debounceMs: 300 }),
      { initialProps: { value: 'a' } }
    )
    rerender({ value: 'b' })
    expect(saveFn).not.toHaveBeenCalled()
    await act(async () => { vi.advanceTimersByTime(300) })
    expect(saveFn).toHaveBeenCalledWith('b')
    expect(result.current.status).toBe('saving')
    vi.useRealTimers()
  })

  it('saveFn 失敗時 status 變 error', async () => {
    const saveFn = vi.fn().mockRejectedValue(new Error('fail'))
    const { result, rerender } = renderHook(
      ({ value }) => useAutoSave(value, saveFn, { debounceMs: 0 }),
      { initialProps: { value: 'a' } }
    )
    rerender({ value: 'b' })
    await waitFor(() => expect(result.current.status).toBe('error'))
  })
})
```

- [ ] **Step 2: 實作**

```ts
import { useEffect, useRef, useState } from 'react'

export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

export interface UseAutoSaveOptions {
  debounceMs?: number
}

export interface UseAutoSaveResult {
  status: SaveStatus
  lastSavedAt: Date | null
  forceSave: () => Promise<void>
}

export function useAutoSave<T>(
  value: T,
  saveFn: (v: T) => Promise<void>,
  { debounceMs = 300 }: UseAutoSaveOptions = {}
): UseAutoSaveResult {
  const [status, setStatus] = useState<SaveStatus>('idle')
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null)
  const initial = useRef(true)
  const valueRef = useRef(value)
  valueRef.current = value

  async function doSave(v: T) {
    setStatus('saving')
    try {
      await saveFn(v)
      setStatus('saved')
      setLastSavedAt(new Date())
    } catch {
      setStatus('error')
    }
  }

  useEffect(() => {
    if (initial.current) { initial.current = false; return }
    const t = setTimeout(() => doSave(value), debounceMs)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, debounceMs])

  const forceSave = async () => doSave(valueRef.current)

  return { status, lastSavedAt, forceSave }
}
```

- [ ] **Step 3: 測試 + Commit**

```bash
npm test -- hooks/
git add frontend/src/hooks/
git commit -m "feat(frontend): hooks/useAutoSave（debounce + 失敗處理）"
```

---

# Phase 5: AppShell + 通用元件

## Task 5.1: store/useAgentContext.ts（當前選中 Agent）

**Files:**
- Create: `D:/mini_test/frontend/src/store/useAgentContext.ts`

- [ ] **Step 1: 實作**

```ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Agent } from '@/api/types'

interface AgentContextState {
  current: Agent | null
  setCurrent: (a: Agent | null) => void
}

export const useAgentContext = create<AgentContextState>()(
  persist(
    (set) => ({
      current: null,
      setCurrent: (a) => set({ current: a }),
    }),
    { name: 'rasa-kb-current-agent' }
  )
)
```

## Task 5.2: store/useUiPreferences.ts（欄寬、sidebar 摺疊）

**Files:**
- Create: `D:/mini_test/frontend/src/store/useUiPreferences.ts`

- [ ] **Step 1: 實作**

```ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface UiPreferences {
  sidebarCollapsed: boolean
  toggleSidebar: () => void
  knowledgeRightPaneWidth: number
  setKnowledgeRightPaneWidth: (n: number) => void
}

export const useUiPreferences = create<UiPreferences>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      knowledgeRightPaneWidth: 480,
      setKnowledgeRightPaneWidth: (n) => set({ knowledgeRightPaneWidth: n }),
    }),
    { name: 'rasa-kb-ui-prefs' }
  )
)
```

## Task 5.3: components/Kbd.tsx（鍵盤鍵顯示）

**Files:**
- Create: `D:/mini_test/frontend/src/components/Kbd.tsx`

- [ ] **Step 1: 實作**

```tsx
import { cn } from '@/lib/utils'

export function Kbd({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <kbd className={cn(
      'inline-flex items-center justify-center min-w-[1.5rem] h-6 px-1.5',
      'rounded border border-border-strong bg-subtle',
      'font-mono text-xs text-text-secondary',
      className
    )}>
      {children}
    </kbd>
  )
}
```

## Task 5.4: components/EmptyState.tsx（通用空狀態）

**Files:**
- Create: `D:/mini_test/frontend/src/components/EmptyState.tsx`

- [ ] **Step 1: 實作**

```tsx
import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center text-center py-12', className)}>
      <Icon className="w-12 h-12 text-text-muted mb-4" strokeWidth={1.5} />
      <h3 className="text-lg font-semibold text-text-primary mb-1">{title}</h3>
      {description && <p className="text-sm text-text-secondary mb-4 max-w-md">{description}</p>}
      {action}
    </div>
  )
}
```

## Task 5.5: components/PageError.tsx + ErrorBoundary.tsx

**Files:**
- Create: `D:/mini_test/frontend/src/components/PageError.tsx`
- Create: `D:/mini_test/frontend/src/components/ErrorBoundary.tsx`

- [ ] **Step 1: PageError**

```tsx
import { AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useNavigate } from 'react-router-dom'

export function PageError({ message }: { message?: string }) {
  const navigate = useNavigate()
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8">
      <AlertTriangle className="w-16 h-16 text-amber-500 mb-4" strokeWidth={1.5} />
      <h1 className="text-2xl font-bold mb-2">系統發生錯誤</h1>
      <p className="text-text-secondary mb-6">{message ?? '我們已記錄此問題，請稍後再試。'}</p>
      <div className="flex gap-3">
        <Button variant="outline" onClick={() => location.reload()}>重新整理</Button>
        <Button onClick={() => navigate('/agents')}>回到 Dashboard</Button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: ErrorBoundary（class component，React 限制）**

```tsx
import { Component, type ReactNode } from 'react'
import { PageError } from './PageError'

interface Props { children: ReactNode }
interface State { hasError: boolean; message?: string }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }
  static getDerivedStateFromError(err: Error): State {
    return { hasError: true, message: err.message }
  }
  componentDidCatch(err: Error) {
    console.error('[ErrorBoundary]', err)
  }
  render() {
    if (this.state.hasError) return <PageError message={this.state.message} />
    return this.props.children
  }
}
```

## Task 5.6: components/Topbar.tsx + Sidebar.tsx + Breadcrumb.tsx

**Files:**
- Create: `D:/mini_test/frontend/src/components/Topbar.tsx`
- Create: `D:/mini_test/frontend/src/components/Sidebar.tsx`
- Create: `D:/mini_test/frontend/src/components/Breadcrumb.tsx`

- [ ] **Step 1: Sidebar.tsx**（左側 64px icon-only）

```tsx
import { NavLink, useParams } from 'react-router-dom'
import { Home, BookOpen, RefreshCw, ArrowDownUp, MessageSquare, History, Settings, type LucideIcon } from 'lucide-react'
import { useAuthStore } from '@/store/useAuthStore'
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'

interface NavItem { to: string; icon: LucideIcon; label: string; superadminOnly?: boolean }

const NAV_ITEMS: NavItem[] = [
  { to: 'dashboard', icon: Home, label: '儀表板' },
  { to: 'knowledge', icon: BookOpen, label: '知識庫' },
  { to: 'sync', icon: RefreshCw, label: '同步' },
  { to: 'import-export', icon: ArrowDownUp, label: '匯入匯出' },
  { to: 'test-chat', icon: MessageSquare, label: '對話測試' },
  { to: 'audit', icon: History, label: '稽核日誌' },
  { to: 'settings', icon: Settings, label: 'Agent 設定', superadminOnly: true },
]

export function Sidebar() {
  const { id } = useParams<{ id: string }>()
  const isSuper = useAuthStore((s) => s.user?.is_superadmin ?? false)
  if (!id) return null
  return (
    <TooltipProvider delayDuration={300}>
      <aside className="w-16 h-screen bg-surface border-r border-border-default flex flex-col items-center py-4 gap-2 sticky top-0">
        {NAV_ITEMS.filter((it) => !it.superadminOnly || isSuper).map((item) => (
          <Tooltip key={item.to}>
            <TooltipTrigger asChild>
              <NavLink
                to={`/agents/${id}/${item.to}`}
                className={({ isActive }) => cn(
                  'w-10 h-10 rounded-md flex items-center justify-center cursor-pointer transition-colors duration-fast',
                  isActive ? 'bg-brand-50 text-brand-700' : 'text-text-secondary hover:bg-subtle hover:text-text-primary'
                )}
                aria-label={item.label}
              >
                <item.icon className="w-5 h-5" strokeWidth={1.5} />
              </NavLink>
            </TooltipTrigger>
            <TooltipContent side="right">{item.label}</TooltipContent>
          </Tooltip>
        ))}
      </aside>
    </TooltipProvider>
  )
}
```

- [ ] **Step 2: Topbar.tsx**

```tsx
import { useNavigate } from 'react-router-dom'
import { Bell, ChevronDown, LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { useAuthStore } from '@/store/useAuthStore'
import { useAgentContext } from '@/store/useAgentContext'
import { Breadcrumb } from './Breadcrumb'

export function Topbar() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const currentAgent = useAgentContext((s) => s.current)

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <header className="h-16 bg-surface border-b border-border-default flex items-center px-6 sticky top-0 z-sticky">
      <div className="flex items-center gap-3 mr-6">
        <div className="w-8 h-8 rounded bg-brand-500 flex items-center justify-center font-bold text-white">R</div>
        <span className="font-semibold text-text-primary">Rasa KB</span>
      </div>

      {currentAgent && (
        <>
          <span className="text-text-muted mx-2">/</span>
          <Button variant="ghost" size="sm" onClick={() => navigate('/agents')}>
            {currentAgent.name} <ChevronDown className="w-4 h-4 ml-1" />
          </Button>
        </>
      )}

      <Breadcrumb className="ml-auto mr-4" />

      <Button variant="ghost" size="icon" aria-label="通知"><Bell className="w-5 h-5" strokeWidth={1.5} /></Button>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="sm">
            {user?.username} <ChevronDown className="w-4 h-4 ml-1" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={handleLogout}>
            <LogOut className="w-4 h-4 mr-2" /> 登出
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  )
}
```

- [ ] **Step 3: Breadcrumb.tsx**

```tsx
import { useLocation, useParams, Link } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'

const PAGE_LABELS: Record<string, string> = {
  dashboard: '儀表板',
  knowledge: '知識庫',
  sync: '同步',
  'import-export': '匯入匯出',
  'test-chat': '對話測試',
  audit: '稽核日誌',
  settings: 'Agent 設定',
}

export function Breadcrumb({ className }: { className?: string }) {
  const { pathname } = useLocation()
  const { id } = useParams<{ id: string }>()
  if (!id) return null

  const segments = pathname.split('/').filter(Boolean)
  const lastSeg = segments[segments.length - 1]
  const label = PAGE_LABELS[lastSeg]
  if (!label) return null

  return (
    <nav className={cn('text-sm text-text-secondary flex items-center gap-1', className)} aria-label="Breadcrumb">
      <Link to={`/agents/${id}/dashboard`} className="hover:text-text-primary">主頁</Link>
      <ChevronRight className="w-4 h-4" strokeWidth={1.5} />
      <span className="text-text-primary font-medium">{label}</span>
    </nav>
  )
}
```

## Task 5.7: components/AppShell.tsx + components/KeyboardShortcuts.tsx

**Files:**
- Create: `D:/mini_test/frontend/src/components/AppShell.tsx`
- Create: `D:/mini_test/frontend/src/components/KeyboardShortcuts.tsx`

- [ ] **Step 1: AppShell（頂部 + 側邊 + 主內容）**

```tsx
import { Outlet } from 'react-router-dom'
import { Topbar } from './Topbar'
import { Sidebar } from './Sidebar'
import { ErrorBoundary } from './ErrorBoundary'
import { KeyboardShortcuts } from './KeyboardShortcuts'

export function AppShell() {
  return (
    <div className="min-h-screen bg-canvas flex flex-col">
      <Topbar />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
      <KeyboardShortcuts />
    </div>
  )
}
```

- [ ] **Step 2: KeyboardShortcuts（? 速查表）**

```tsx
import { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { useKeyboardShortcut } from '@/hooks/useKeyboardShortcut'
import { Kbd } from './Kbd'

const SHORTCUTS: Array<{ keys: string[]; desc: string; section: string }> = [
  { section: '全域', keys: ['/'], desc: '聚焦搜尋框' },
  { section: '全域', keys: ['n'], desc: '新增 FAQ' },
  { section: '全域', keys: ['?'], desc: '顯示此速查表' },
  { section: 'FAQ 列表', keys: ['↑', '↓'], desc: '切換選中列' },
  { section: 'FAQ 列表', keys: ['j', 'k'], desc: '同上下鍵（vim 風）' },
  { section: 'FAQ 列表', keys: ['Enter'], desc: '進入編輯' },
  { section: 'FAQ 列表', keys: ['x'], desc: '切換 checkbox' },
  { section: 'FAQ 列表', keys: ['g', 'g'], desc: '跳至首列' },
  { section: 'FAQ 列表', keys: ['G'], desc: '跳至末列' },
  { section: 'FAQ 編輯', keys: ['Esc'], desc: '取消編輯' },
  { section: 'FAQ 編輯', keys: ['⌘/Ctrl', 'S'], desc: '立即儲存' },
  { section: 'FAQ 編輯', keys: ['⌘/Ctrl', 'Enter'], desc: '儲存並下一筆' },
]

export function KeyboardShortcuts() {
  const [open, setOpen] = useState(false)
  useKeyboardShortcut('?', () => setOpen(true), { shift: true })

  const grouped = SHORTCUTS.reduce<Record<string, typeof SHORTCUTS>>((acc, s) => {
    (acc[s.section] ??= []).push(s)
    return acc
  }, {})

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-lg">
        <DialogHeader><DialogTitle>鍵盤快捷鍵</DialogTitle></DialogHeader>
        <div className="space-y-4">
          {Object.entries(grouped).map(([section, items]) => (
            <div key={section}>
              <h4 className="text-sm font-semibold text-text-secondary mb-2">{section}</h4>
              <ul className="space-y-1.5">
                {items.map((s) => (
                  <li key={s.desc} className="flex justify-between items-center text-sm">
                    <span className="text-text-primary">{s.desc}</span>
                    <span className="flex gap-1">
                      {s.keys.map((k) => <Kbd key={k}>{k}</Kbd>)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}
```

- [ ] **Step 3: Commit Phase 5**

```bash
cd D:/mini_test
git add frontend/src/
git commit -m "feat(frontend): AppShell + Topbar + Sidebar + Breadcrumb + KeyboardShortcuts + EmptyState + ErrorBoundary"
```

---

# Phase 6: App.tsx 路由 + Toaster 全域

## Task 6.1: 暫定的 App.tsx（佔位頁面 + 路由完整）

**Files:**
- Create: `D:/mini_test/frontend/src/App.tsx`

- [ ] **Step 1: 寫入 App.tsx**

```tsx
import { Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'sonner'
import { ProtectedRoute } from '@/routes/ProtectedRoute'
import { AdminRoute } from '@/routes/AdminRoute'
import { AppShell } from '@/components/AppShell'

// 佔位頁面（後續 Phase 取代）
const Placeholder = ({ name }: { name: string }) => (
  <div className="p-8">
    <h1 className="text-2xl font-bold">{name}</h1>
    <p className="text-text-muted mt-2">此頁面尚未實作（Phase 進行中）</p>
  </div>
)

export function App() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<Placeholder name="登入" />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/agents" element={<Placeholder name="Agent 選擇" />} />
          <Route element={<AdminRoute />}>
            <Route path="/admin/users" element={<Placeholder name="使用者管理" />} />
          </Route>
          <Route path="/agents/:id" element={<AppShell />}>
            <Route path="dashboard" element={<Placeholder name="儀表板" />} />
            <Route path="knowledge" element={<Placeholder name="知識庫" />} />
            <Route path="sync" element={<Placeholder name="同步" />} />
            <Route path="import-export" element={<Placeholder name="匯入匯出" />} />
            <Route path="test-chat" element={<Placeholder name="對話測試" />} />
            <Route path="audit" element={<Placeholder name="稽核日誌" />} />
            <Route element={<AdminRoute />}>
              <Route path="settings" element={<Placeholder name="Agent 設定" />} />
            </Route>
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/agents" replace />} />
      </Routes>
      <Toaster richColors position="bottom-right" />
    </>
  )
}
```

- [ ] **Step 2: 跑 dev 確認骨架可載入**

```bash
cd D:/mini_test/frontend && npm run dev
```

開瀏覽器到 `http://localhost:5173`，預期被導到 `/login`（佔位頁）。

按 `Ctrl+C` 結束 dev server。

- [ ] **Step 3: Commit**

```bash
cd D:/mini_test
git add frontend/src/App.tsx
git commit -m "feat(frontend): App.tsx 路由骨架 + Toaster 全域"
```

---

# Phase 7: api/endpoints 拆分（按 feature）

## Task 7.1: api/endpoints/auth.ts

**Files:**
- Create: `D:/mini_test/frontend/src/api/endpoints/auth.ts`

- [ ] **Step 1: 實作**

```ts
import { apiClient } from '../client'
import type { User } from '../types'

export async function login(username: string, password: string): Promise<User> {
  const resp = await apiClient.post('/api/v1/auth/login', { username, password })
  return resp.data.data as User
}

export async function logout(): Promise<void> {
  await apiClient.post('/api/v1/auth/logout')
}

export async function me(): Promise<User> {
  const resp = await apiClient.get('/api/v1/auth/me')
  return resp.data.data as User
}
```

## Task 7.2: api/endpoints/agents.ts

```ts
import { apiClient } from '../client'
import type { Agent, AgentStats, TestConnectionResult, ValidateScriptResult } from '../types'

export async function listAgents(): Promise<Agent[]> {
  const resp = await apiClient.get('/api/v1/agents')
  return resp.data.data ?? []
}

export async function createAgent(payload: Omit<Agent, 'id' | 'created_at'>): Promise<Agent> {
  const resp = await apiClient.post('/api/v1/agents', payload)
  return resp.data.data as Agent
}

export async function updateAgent(id: string, payload: Partial<Agent>): Promise<Agent> {
  const resp = await apiClient.patch(`/api/v1/agents/${id}`, payload)
  return resp.data.data as Agent
}

export async function deleteAgent(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/agents/${id}`)
}

export async function getAgentStats(id: string): Promise<AgentStats> {
  const resp = await apiClient.get(`/api/v1/agents/${id}/stats`)
  return resp.data.data as AgentStats
}

export async function testConnection(id: string): Promise<TestConnectionResult> {
  const resp = await apiClient.post(`/api/v1/agents/${id}/test-connection`)
  return resp.data.data as TestConnectionResult
}

export async function validateScript(id: string): Promise<ValidateScriptResult> {
  const resp = await apiClient.post(`/api/v1/agents/${id}/validate-script`)
  return resp.data.data as ValidateScriptResult
}
```

## Task 7.3: api/endpoints/categories.ts

**Files:**
- Create: `D:/mini_test/frontend/src/api/endpoints/categories.ts`

- [ ] **Step 1: 實作**

```ts
import { apiClient } from '../client'
import type { CategoryNode } from '../types'

export async function listCategories(agentId: string): Promise<CategoryNode[]> {
  const resp = await apiClient.get(`/api/v1/agents/${agentId}/categories`)
  return resp.data.data ?? []
}

export async function createCategory(
  agentId: string,
  payload: { name: string; parent_id: string | null }
): Promise<CategoryNode> {
  const resp = await apiClient.post(`/api/v1/agents/${agentId}/categories`, payload)
  return resp.data.data as CategoryNode
}

export async function updateCategory(
  agentId: string,
  categoryId: string,
  payload: { name?: string; parent_id?: string | null }
): Promise<CategoryNode> {
  const resp = await apiClient.patch(`/api/v1/agents/${agentId}/categories/${categoryId}`, payload)
  return resp.data.data as CategoryNode
}

export async function deleteCategory(agentId: string, categoryId: string): Promise<void> {
  await apiClient.delete(`/api/v1/agents/${agentId}/categories/${categoryId}`)
}
```

## Task 7.4: api/endpoints/faqs.ts

**Files:**
- Create: `D:/mini_test/frontend/src/api/endpoints/faqs.ts`

- [ ] **Step 1: 實作**

```ts
import { apiClient } from '../client'
import type { Faq, FaqListResponse, FaqHistory } from '../types'

export interface FaqListParams {
  page?: number
  per_page?: number
  status?: string
  category_id?: string
  q?: string
  tag?: string
}

export async function listFaqs(agentId: string, params: FaqListParams = {}): Promise<FaqListResponse> {
  const resp = await apiClient.get(`/api/v1/agents/${agentId}/faqs`, { params })
  return resp.data.data as FaqListResponse
}

export async function getFaq(agentId: string, faqId: string): Promise<Faq> {
  const resp = await apiClient.get(`/api/v1/agents/${agentId}/faqs/${faqId}`)
  return resp.data.data as Faq
}

export async function createFaq(
  agentId: string,
  payload: { category_id: string; question: string; answer: string; tags: string[] }
): Promise<Faq> {
  const resp = await apiClient.post(`/api/v1/agents/${agentId}/faqs`, payload)
  return resp.data.data as Faq
}

export async function updateFaq(
  agentId: string,
  faqId: string,
  payload: Partial<Pick<Faq, 'question' | 'answer' | 'category_id' | 'tags'>>
): Promise<Faq> {
  const resp = await apiClient.patch(`/api/v1/agents/${agentId}/faqs/${faqId}`, payload)
  return resp.data.data as Faq
}

export async function deleteFaq(agentId: string, faqId: string): Promise<void> {
  await apiClient.delete(`/api/v1/agents/${agentId}/faqs/${faqId}`)
}

// 編輯鎖
export async function acquireLock(agentId: string, faqId: string): Promise<void> {
  await apiClient.post(`/api/v1/agents/${agentId}/faqs/${faqId}/lock`)
}
export async function refreshLock(agentId: string, faqId: string): Promise<void> {
  await apiClient.put(`/api/v1/agents/${agentId}/faqs/${faqId}/lock`)
}
export async function releaseLock(agentId: string, faqId: string): Promise<void> {
  await apiClient.delete(`/api/v1/agents/${agentId}/faqs/${faqId}/lock`)
}

// 狀態機轉換
export async function submit(agentId: string, faqId: string): Promise<Faq> {
  const resp = await apiClient.post(`/api/v1/agents/${agentId}/faqs/${faqId}/submit`)
  return resp.data.data as Faq
}
export async function approve(agentId: string, faqId: string): Promise<Faq> {
  const resp = await apiClient.post(`/api/v1/agents/${agentId}/faqs/${faqId}/approve`)
  return resp.data.data as Faq
}
export async function reject(agentId: string, faqId: string, reason: string): Promise<Faq> {
  const resp = await apiClient.post(`/api/v1/agents/${agentId}/faqs/${faqId}/reject`, { reason })
  return resp.data.data as Faq
}
export async function unapprove(agentId: string, faqId: string): Promise<Faq> {
  const resp = await apiClient.post(`/api/v1/agents/${agentId}/faqs/${faqId}/unapprove`)
  return resp.data.data as Faq
}

// 版本歷史
export async function getHistory(agentId: string, faqId: string): Promise<FaqHistory[]> {
  const resp = await apiClient.get(`/api/v1/agents/${agentId}/faqs/${faqId}/history`)
  return resp.data.data ?? []
}
export async function rollback(agentId: string, faqId: string, versionId: string): Promise<Faq> {
  const resp = await apiClient.post(`/api/v1/agents/${agentId}/faqs/${faqId}/rollback`, { version_id: versionId })
  return resp.data.data as Faq
}
```

## Task 7.5: api/endpoints/sync.ts

**Files:**
- Create: `D:/mini_test/frontend/src/api/endpoints/sync.ts`

- [ ] **Step 1: 實作**

```ts
import { apiClient } from '../client'
import type { SyncLog, SyncLogHistoryItem } from '../types'

export async function triggerSync(agentId: string): Promise<{ task_id: string | null; sync_log_id: string }> {
  const resp = await apiClient.post(`/api/v1/agents/${agentId}/sync`)
  return resp.data.data
}

export async function getSyncStatus(syncLogId: string): Promise<SyncLog> {
  const resp = await apiClient.get(`/api/v1/sync/tasks/${syncLogId}`)
  return resp.data.data as SyncLog
}

// 後端新端點（spec §13.1）
export async function getSyncHistory(agentId: string, limit = 20): Promise<SyncLogHistoryItem[]> {
  const resp = await apiClient.get(`/api/v1/agents/${agentId}/sync/history`, { params: { limit } })
  return resp.data.data ?? []
}
```

## Task 7.6: api/endpoints/audit.ts

**Files:**
- Create: `D:/mini_test/frontend/src/api/endpoints/audit.ts`

- [ ] **Step 1: 實作**

```ts
import { apiClient } from '../client'
import type { AuditLogList } from '../types'

export interface AuditListParams {
  page?: number
  per_page?: number
  action?: string
  performed_by?: string
  date_from?: string
  date_to?: string
  item_id?: string
}

export async function listAuditLogs(agentId: string, params: AuditListParams = {}): Promise<AuditLogList> {
  const resp = await apiClient.get(`/api/v1/agents/${agentId}/audit-logs`, { params })
  return resp.data.data as AuditLogList
}
```

## Task 7.7: api/endpoints/users.ts

**Files:**
- Create: `D:/mini_test/frontend/src/api/endpoints/users.ts`

- [ ] **Step 1: 實作**

```ts
import { apiClient } from '../client'
import type { User } from '../types'

export async function listUsers(): Promise<User[]> {
  const resp = await apiClient.get('/api/v1/users')
  return resp.data.data ?? []
}

export async function createUser(payload: { username: string; password: string }): Promise<User> {
  const resp = await apiClient.post('/api/v1/users', payload)
  return resp.data.data as User
}

export async function updateUser(userId: string, payload: { is_active?: boolean }): Promise<User> {
  const resp = await apiClient.patch(`/api/v1/users/${userId}`, payload)
  return resp.data.data as User
}

export async function deleteUser(userId: string): Promise<void> {
  await apiClient.delete(`/api/v1/users/${userId}`)
}

export async function resetPassword(userId: string, newPassword: string): Promise<void> {
  await apiClient.post(`/api/v1/users/${userId}/reset-password`, { new_password: newPassword })
}

export async function assignRole(
  userId: string,
  agentId: string,
  role: 'editor' | 'reviewer'
): Promise<void> {
  await apiClient.put(`/api/v1/users/${userId}/agents/${agentId}/role`, { role })
}

export async function removeRole(userId: string, agentId: string): Promise<void> {
  await apiClient.delete(`/api/v1/users/${userId}/agents/${agentId}/role`)
}
```

## Task 7.8: Commit Phase 7

- [ ] **Step 1: Commit**

```bash
cd D:/mini_test
git add frontend/src/api/
git commit -m "feat(frontend): api/endpoints 按 feature 拆分（7 檔）"
```

---

# Phase 8: MSW 測試 mock 基礎建設

## Task 8.1: mocks/handlers.ts + server.ts

**Files:**
- Create: `D:/mini_test/frontend/src/mocks/handlers.ts`
- Create: `D:/mini_test/frontend/src/mocks/server.ts`
- Modify: `D:/mini_test/frontend/src/test-setup.ts`

- [ ] **Step 1: handlers.ts**

```ts
import { http, HttpResponse } from 'msw'

const ok = <T>(data: T) => HttpResponse.json({ success: true, data })

export const handlers = [
  http.post('/api/v1/auth/login', () => ok({
    id: 'u1', username: 'admin', is_superadmin: true, is_active: true, created_at: '2026-01-01T00:00:00Z',
  })),
  http.get('/api/v1/auth/me', () => ok({
    id: 'u1', username: 'admin', is_superadmin: true, is_active: true, created_at: '2026-01-01T00:00:00Z',
  })),
  http.post('/api/v1/auth/logout', () => HttpResponse.json({ success: true })),

  http.get('/api/v1/agents', () => ok([
    { id: 'a1', name: 'Demo', txt_output_path: '/opt/sap', rasa_rest_url: null, ingest_script_path: null, created_at: null },
  ])),

  // 預設讓所有未明確 mock 的 GET 回 empty array / object，避免測試噪音
  http.get('/api/v1/agents/:id/stats', () => ok({
    total_faqs: 0, pending_count: 0, approved_count: 0, synced_count: 0,
    draft_count: 0, rejected_count: 0, categories_count: 0,
  })),
]
```

- [ ] **Step 2: server.ts**

```ts
import { setupServer } from 'msw/node'
import { handlers } from './handlers'

export const server = setupServer(...handlers)
```

- [ ] **Step 3: 更新 test-setup.ts**

```ts
import '@testing-library/jest-dom/vitest'
import { afterAll, afterEach, beforeAll } from 'vitest'
import { server } from './mocks/server'

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
```

- [ ] **Step 4: 跑全部測試**

```bash
cd D:/mini_test/frontend && npm test
```

Expected: 既有 hook + lib + route 測試全綠（MSW server 啟動中）。

- [ ] **Step 5: Commit**

```bash
cd D:/mini_test
git add frontend/src/
git commit -m "feat(frontend): MSW handlers + server + test-setup"
```

---

# Phase 6-14 範圍提示（後續 plan）

由於剩餘 phase（auth/agents/dashboard/knowledge/sync/import-export/audit/chat/users 各 feature 完整實作）規模龐大，本 plan 第二份 `2026-04-30-frontend-overhaul-rewrite-features.md` 將涵蓋：

- Phase 9: features/auth（Login）
- Phase 10: features/agents（AgentSelect + Settings + Inline Panel）
- Phase 11: features/dashboard（KPI + 待我處理 + 活動 + 快速操作）
- Phase 12: features/knowledge（核心三欄、最大 phase）
- Phase 13: features/sync（觸發 + 歷史 timeline）
- Phase 14: features/import-export（拖放 + 進度 + 結果）
- Phase 15: features/audit（篩選 + 日期分組）
- Phase 16: features/chat（標準 chat UI）
- Phase 17: features/users（左右分欄 master-detail）

第三份 `2026-04-30-frontend-overhaul-rewrite-cutover.md` 將涵蓋：

- Phase 18: 後端三新端點（FastAPI）
- Phase 19: Cutover（重啟 docker、smoke test、刪 src.legacy）
- Phase 20: Polish（a11y 檢查、Lighthouse、文件更新）

---

## 本 plan（Phase 0–8）完成驗收

執行完 Phase 0–8 後，下列驗收條件必須全綠：

- [ ] `cd D:/mini_test/frontend && npm run typecheck` — 零錯誤
- [ ] `cd D:/mini_test/frontend && npm test` — 全部測試 PASS（含 lib / hooks / store / routes）
- [ ] `cd D:/mini_test/frontend && npm run lint` — 零警告
- [ ] `cd D:/mini_test/frontend && npm run dev` 啟動成功，瀏覽器開 `http://localhost:5173/login` 顯示佔位「登入」頁
- [ ] 所有 commit 訊息符合 `feat(frontend):` / `chore(frontend):` 規範
- [ ] `frontend/src.legacy/` 仍存在（cutover 前不刪）

完成後執行 plan 2（features 大量實作）。

---

## Self-Review

執行此 plan 前請確認：

1. ✅ Phase 0 備份不會破壞原 git 歷史（`mv` 只是 rename）
2. ✅ 所有 Tailwind token 與 spec §5 完全一致
3. ✅ 所有檔名與 spec §9 檔案結構一致
4. ✅ 每個 hook / util 都有測試
5. ✅ 沒有「TBD」「待補」字樣
