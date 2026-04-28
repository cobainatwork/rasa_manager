import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { DialogContainer } from './DialogContainer'
import { useDialogStore } from '@/store/useDialogStore'
import type { DialogEntry } from '@/store/useDialogStore'

// DialogEntry.resolve 必填；測試中由 _resolve mock 驅動，此處僅滿足型別約束
const noop: DialogEntry['resolve'] = () => {}

beforeEach(() => {
  useDialogStore.setState({ dialogs: [] })
})

describe('DialogContainer — 空狀態', () => {
  it('無 dialog 時不渲染任何內容', () => {
    const { container } = render(<DialogContainer />)
    expect(container.firstChild).toBeNull()
  })
})

describe('DialogContainer — confirm dialog', () => {
  it('顯示 confirm 訊息', () => {
    useDialogStore.setState({
      dialogs: [{ id: 'd1', type: 'confirm', message: '確定要刪除？', resolve: noop }],
    })
    render(<DialogContainer />)
    expect(screen.getByText('確定要刪除？')).toBeDefined()
  })

  it('confirm：點擊確定呼叫 _resolve(id, true)', () => {
    const _resolve = vi.fn()
    useDialogStore.setState({
      dialogs: [{ id: 'd1', type: 'confirm', message: '確定？', resolve: noop }],
      _resolve,
    })
    render(<DialogContainer />)
    fireEvent.click(screen.getByText('確定'))
    expect(_resolve).toHaveBeenCalledWith('d1', true)
  })

  it('confirm：點擊取消呼叫 _resolve(id, false)', () => {
    const _resolve = vi.fn()
    useDialogStore.setState({
      dialogs: [{ id: 'd1', type: 'confirm', message: '確定？', resolve: noop }],
      _resolve,
    })
    render(<DialogContainer />)
    fireEvent.click(screen.getByText('取消'))
    expect(_resolve).toHaveBeenCalledWith('d1', false)
  })

  it('confirm 不顯示 input 欄位', () => {
    useDialogStore.setState({
      dialogs: [{ id: 'd1', type: 'confirm', message: '確定？', resolve: noop }],
    })
    render(<DialogContainer />)
    expect(screen.queryByRole('textbox')).toBeNull()
  })
})

describe('DialogContainer — prompt dialog', () => {
  it('顯示 prompt 訊息與 input', () => {
    useDialogStore.setState({
      dialogs: [{ id: 'd2', type: 'prompt', message: '請輸入名稱', resolve: noop }],
    })
    render(<DialogContainer />)
    expect(screen.getByText('請輸入名稱')).toBeDefined()
    expect(screen.getByRole('textbox')).toBeDefined()
  })

  it('prompt：defaultValue 預填入 input', () => {
    useDialogStore.setState({
      dialogs: [{ id: 'd2', type: 'prompt', message: '請輸入', defaultValue: '預設值', resolve: noop }],
    })
    render(<DialogContainer />)
    const input = screen.getByRole('textbox') as HTMLInputElement
    expect(input.value).toBe('預設值')
  })

  it('prompt：點擊確定傳入 inputValue（非空）', () => {
    const _resolve = vi.fn()
    useDialogStore.setState({
      dialogs: [{ id: 'd2', type: 'prompt', message: '請輸入', resolve: noop }],
      _resolve,
    })
    render(<DialogContainer />)
    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: '用戶輸入' } })
    fireEvent.click(screen.getByText('確定'))
    expect(_resolve).toHaveBeenCalledWith('d2', '用戶輸入')
  })

  it('prompt：點擊取消傳入 null', () => {
    const _resolve = vi.fn()
    useDialogStore.setState({
      dialogs: [{ id: 'd2', type: 'prompt', message: '請輸入', resolve: noop }],
      _resolve,
    })
    render(<DialogContainer />)
    fireEvent.click(screen.getByText('取消'))
    expect(_resolve).toHaveBeenCalledWith('d2', null)
  })

  it('prompt：Enter 鍵觸發確定', () => {
    const _resolve = vi.fn()
    useDialogStore.setState({
      dialogs: [{ id: 'd2', type: 'prompt', message: '請輸入', defaultValue: '已填', resolve: noop }],
      _resolve,
    })
    render(<DialogContainer />)
    const input = screen.getByRole('textbox')
    fireEvent.keyDown(input, { key: 'Enter' })
    expect(_resolve).toHaveBeenCalledWith('d2', '已填')
  })

  it('prompt：Escape 鍵觸發取消（回傳 null）', () => {
    const _resolve = vi.fn()
    useDialogStore.setState({
      dialogs: [{ id: 'd2', type: 'prompt', message: '請輸入', resolve: noop }],
      _resolve,
    })
    render(<DialogContainer />)
    const input = screen.getByRole('textbox')
    fireEvent.keyDown(input, { key: 'Escape' })
    expect(_resolve).toHaveBeenCalledWith('d2', null)
  })

  it('prompt：空字串輸入後確定傳入 null', () => {
    const _resolve = vi.fn()
    useDialogStore.setState({
      dialogs: [{ id: 'd2', type: 'prompt', message: '請輸入', resolve: noop }],
      _resolve,
    })
    render(<DialogContainer />)
    // input 預設值為空字串，直接點確定 → null
    fireEvent.click(screen.getByText('確定'))
    expect(_resolve).toHaveBeenCalledWith('d2', null)
  })
})

describe('DialogContainer — 多則 dialog 只顯示第一則', () => {
  it('只渲染 dialogs[0]', () => {
    useDialogStore.setState({
      dialogs: [
        { id: 'da', type: 'confirm', message: '第一則', resolve: noop },
        { id: 'db', type: 'confirm', message: '第二則', resolve: noop },
      ],
    })
    render(<DialogContainer />)
    expect(screen.getByText('第一則')).toBeDefined()
    expect(screen.queryByText('第二則')).toBeNull()
  })
})
