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
