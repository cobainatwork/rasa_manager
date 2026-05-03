import { Component, type ErrorInfo, type ReactNode } from 'react'
import { PageError } from './PageError'

interface Props {
  children: ReactNode
  /** N10：可注入錯誤上報 hook（例如 Sentry），預設 console.error */
  reportError?: (err: Error, info: ErrorInfo) => void
}
interface State { hasError: boolean; message?: string }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(err: Error): State {
    return { hasError: true, message: err.message }
  }

  componentDidCatch(err: Error, info: ErrorInfo) {
    if (this.props.reportError) {
      this.props.reportError(err, info)
    } else {
      console.error('[ErrorBoundary]', err, info)
    }
  }

  /** I14：重置錯誤狀態，由 PageError 的「重新整理」改為呼叫此方法 */
  reset = () => {
    this.setState({ hasError: false, message: undefined })
  }

  render() {
    if (this.state.hasError) {
      return <PageError message={this.state.message} onReset={this.reset} />
    }
    return this.props.children
  }
}
