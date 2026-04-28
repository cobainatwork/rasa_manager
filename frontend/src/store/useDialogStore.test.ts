import { describe, it, expect, beforeEach } from 'vitest'
import { useDialogStore } from './useDialogStore'

beforeEach(() => {
  useDialogStore.setState({ dialogs: [] })
})

describe('useDialogStore — showConfirm', () => {
  it('showConfirm 新增一則 confirm dialog', () => {
    useDialogStore.getState().showConfirm('確定嗎？')
    expect(useDialogStore.getState().dialogs).toHaveLength(1)
    expect(useDialogStore.getState().dialogs[0].type).toBe('confirm')
    expect(useDialogStore.getState().dialogs[0].message).toBe('確定嗎？')
  })

  it('_resolve true 移除 dialog 並 resolve', async () => {
    const promise = useDialogStore.getState().showConfirm('確定嗎？')
    const id = useDialogStore.getState().dialogs[0].id
    useDialogStore.getState()._resolve(id, true)
    expect(await promise).toBe(true)
    expect(useDialogStore.getState().dialogs).toHaveLength(0)
  })

  it('_resolve false 回傳 false', async () => {
    const promise = useDialogStore.getState().showConfirm('確定嗎？')
    const id = useDialogStore.getState().dialogs[0].id
    useDialogStore.getState()._resolve(id, false)
    expect(await promise).toBe(false)
  })
})

describe('useDialogStore — showPrompt', () => {
  it('showPrompt 新增一則 prompt dialog', () => {
    useDialogStore.getState().showPrompt('請輸入名稱', '預設值')
    const dialog = useDialogStore.getState().dialogs[0]
    expect(dialog.type).toBe('prompt')
    expect(dialog.message).toBe('請輸入名稱')
    expect(dialog.defaultValue).toBe('預設值')
  })

  it('_resolve 字串 回傳輸入值', async () => {
    const promise = useDialogStore.getState().showPrompt('請輸入')
    const id = useDialogStore.getState().dialogs[0].id
    useDialogStore.getState()._resolve(id, '用戶輸入')
    expect(await promise).toBe('用戶輸入')
  })

  it('_resolve null 回傳 null（取消）', async () => {
    const promise = useDialogStore.getState().showPrompt('請輸入')
    const id = useDialogStore.getState().dialogs[0].id
    useDialogStore.getState()._resolve(id, null)
    expect(await promise).toBeNull()
  })

  it('多則 dialog 各自獨立', () => {
    useDialogStore.getState().showConfirm('第一')
    useDialogStore.getState().showPrompt('第二')
    expect(useDialogStore.getState().dialogs).toHaveLength(2)
    expect(useDialogStore.getState().dialogs[0].message).toBe('第一')
    expect(useDialogStore.getState().dialogs[1].message).toBe('第二')
  })
})
