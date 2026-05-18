# Frontend — Rasa RAG 知識庫管理平台

React 18 + Vite 5 + TypeScript 5 的單頁應用，透過 `/api` proxy 連接後端 FastAPI。

## 技術棧

| 分類 | 套件 |
|------|------|
| UI 框架 | React 18、Vite 5 |
| 型別 | TypeScript 5（strict mode） |
| 樣式 | Tailwind CSS 3、shadcn/ui（Radix UI） |
| 狀態管理 | Zustand |
| 表單 | React Hook Form + Zod |
| 路由 | React Router v6 |
| API 客戶端 | Axios（含 401 refresh interceptor） |
| 通知 | Sonner |
| 測試 | Vitest、React Testing Library、jest-axe |
| E2E | Playwright |

## 開發指令

```bash
# 安裝依賴
npm install

# 啟動 dev server（proxy /api → http://localhost:8050）
npm run dev

# 執行單元測試（watch mode）
npm test

# 執行單元測試（CI 一次性）
npm test -- --run

# TypeScript 型別檢查
npx tsc --noEmit

# ESLint
npm run lint

# Production build
npm run build

# E2E（需後端服務運行中）
npx playwright test
```

## 專案結構

```
src/
├── api/
│   ├── client.ts            # Axios instance + refresh interceptor
│   ├── endpoints/           # 各資源的 API 函式（faqs / agents / sync / ...）
│   ├── request.ts           # unwrap helper（統一解包 ApiSuccess<T>）
│   └── types.ts             # 所有 API 回應型別定義
├── components/
│   ├── ui/                  # shadcn/ui 元件（Button / Card / Dialog / ...）
│   ├── Topbar.tsx           # 全域頂部導覽
│   ├── Breadcrumb.tsx       # 路徑麵包屑
│   └── EmptyState.tsx       # 空狀態佔位元件
├── features/
│   ├── agents/              # Agent 選擇 / 設定頁
│   ├── audit/               # 稽核日誌頁
│   ├── auth/                # 登入頁 + useLogin hook
│   ├── chat/                # Rasa 對話測試頁
│   ├── dashboard/           # 儀表板（KPI / 待審核 / 活動流）
│   ├── import-export/       # Excel 匯入 / 匯出頁
│   ├── knowledge/           # FAQ 知識庫主頁面（分類樹 / 列表 / 詳情）
│   ├── sync/                # 一鍵同步觸發 / 歷史頁
│   └── users/               # 使用者管理頁（Superadmin）
├── hooks/                   # 共用 hooks（useDebounce / useAutoSave / ...）
├── lib/                     # 純函式工具（diff / format / categories / ...）
├── mocks/                   # MSW request handlers（開發 / 測試用）
├── routes/                  # 路由守衛（ProtectedRoute / AdminRoute / AuthProvider）
└── store/
    ├── useAuthStore.ts      # 全域認證狀態（user / login / logout）
    └── useAgentContext.ts   # 目前選取的 Agent
```

## 核心架構決策

### Feature-based 目錄結構

每個 feature 包含該功能所有的 hooks、元件與型別，相關程式碼聚合於同一目錄，跨 feature 共用的邏輯放 `components/` 或 `hooks/`。

### API 層

- `apiClient`（Axios）負責所有 HTTP 通訊，統一以 `unwrap()` 解包後端 `ApiSuccess<T>` 結構。
- 401 回應由 interceptor 自動嘗試 refresh token，並以 pending queue 防止競態條件。

### 認證

- JWT 儲存於 HttpOnly Cookie（前端無法直接讀取），`useAuthStore` 透過 `/api/v1/auth/me` 取得使用者資訊。
- `AuthProvider` 在 App 掛載時呼叫 `initialize()`，確保頁面重整後自動還原登入狀態。

### 設計 Token

`tailwind.config.ts` 定義自訂 token：
- `brand-*`：主品牌色（藍色系）
- `canvas` / `surface` / `subtle`：背景層次
- `text-primary` / `text-secondary` / `text-muted`：文字層次
- `z-sticky`（20）/ `z-overlay`（30）/ `z-modal`（40）：z-index 層級
- macOS 風格半透明 header：`bg-[#F2F2F7]/80 backdrop-blur-xl`

## 環境變數

Vite dev server 透過 `vite.config.ts` 的 proxy 設定，將 `/api` 轉發至後端，無需在前端設定 `VITE_API_URL`。

Production build 後由 nginx 的 `proxy_pass` 處理轉發（見 `nginx.conf`）。
