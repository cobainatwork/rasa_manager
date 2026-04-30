import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ToastContainer } from './ToastContainer'
import { useToastStore } from '@/store/useToastStore'

beforeEach(() => {
  useToastStore.setState({ toasts: [] })
})

describe('ToastContainer', () => {
  it('沒有 toast 時不渲染任何內容', () => {
    const { container } = render(<ToastContainer />)
    expect(container.firstChild).toBeNull()
  })

  it('有 toast 時正確渲染訊息', () => {
    useToastStore.setState({
      toasts: [{ id: '1', message: '操作成功', type: 'success' }],
    })
    render(<ToastContainer />)
    expect(screen.getByText('操作成功')).toBeDefined()
  })

  it('error type 套用 bg-red-600 樣式', () => {
    useToastStore.setState({
      toasts: [{ id: '2', message: '發生錯誤', type: 'error' }],
    })
    render(<ToastContainer />)
    const toastEl = screen.getByText('發生錯誤').closest('div')
    expect(toastEl?.className).toContain('bg-red-600')
  })

  it('success type 套用 bg-green-600 樣式', () => {
    useToastStore.setState({
      toasts: [{ id: '3', message: '成功', type: 'success' }],
    })
    render(<ToastContainer />)
    const toastEl = screen.getByText('成功').closest('div')
    expect(toastEl?.className).toContain('bg-green-600')
  })

  it('點擊 × 呼叫 removeToast', () => {
    const removeToast = vi.fn()
    useToastStore.setState({
      toasts: [{ id: '4', message: '可關閉', type: 'info' }],
      removeToast,
    })
    render(<ToastContainer />)
    const closeBtn = screen.getByRole('button')
    fireEvent.click(closeBtn)
    expect(removeToast).toHaveBeenCalledWith('4')
  })

  it('多則 toast 全部渲染', () => {
    useToastStore.setState({
      toasts: [
        { id: 'a', message: '第一則', type: 'info' },
        { id: 'b', message: '第二則', type: 'error' },
      ],
    })
    render(<ToastContainer />)
    expect(screen.getByText('第一則')).toBeDefined()
    expect(screen.getByText('第二則')).toBeDefined()
  })
})
