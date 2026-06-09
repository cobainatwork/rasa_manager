// endpoints 共用型別。`Paginated<T>` 已提升至 `@/api/types`，此處只保留查詢參數。

export interface PaginationParams {
  page?: number
  per_page?: number
}

export type { Paginated } from '../types'
