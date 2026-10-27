import { Component } from 'react'
import { ErrorPage } from '../pages/ErrorPages'

// If a page crashes while rendering, show "Something went wrong" instead of a blank screen.
// React only supports this as a class component (there's no hook for catching render errors).

type State = { failed: boolean }

export default class ErrorBoundary extends Component<{ children: React.ReactNode }, State> {
  state: State = { failed: false }

  static getDerivedStateFromError(): State {
    return { failed: true }
  }

  componentDidCatch(error: unknown) {
    console.error(error)
  }

  render() {
    if (this.state.failed) return <ErrorPage onRetry={() => this.setState({ failed: false })} />
    return this.props.children
  }
}
