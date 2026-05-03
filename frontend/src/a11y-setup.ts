import { expect } from 'vitest'
import { toHaveNoViolations } from 'jest-axe'

// 將 jest-axe 的 matcher 接入 vitest 的 expect
expect.extend(toHaveNoViolations)

// jsdom 缺 ResizeObserver / IntersectionObserver，補 polyfill 以利 react-resizable-panels 等元件
if (typeof globalThis.ResizeObserver === 'undefined') {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver
}
if (typeof globalThis.IntersectionObserver === 'undefined') {
  globalThis.IntersectionObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
    takeRecords() { return [] }
    root = null
    rootMargin = ''
    thresholds = []
  } as unknown as typeof IntersectionObserver
}
