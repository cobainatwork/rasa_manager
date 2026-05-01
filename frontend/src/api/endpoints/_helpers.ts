// I2：endpoints 共用型別。pagination 結構在 audit.ts、faqs.ts 重複，集中於此。

export interface PaginationParams {
  page?: number
  per_page?: number
}

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  per_page: number
}
