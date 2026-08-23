import { Component, type ErrorInfo, type ReactNode } from 'react';

import styles from './ErrorBoundary.module.css';

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Names the region that failed, so the message says what broke. */
  regionLabel: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

/**
 * Catches render errors within one subtree.
 *
 * rules/frontend.md requires boundaries at meaningful subtree boundaries so a
 * single component failure cannot blank the page, and requires that the user
 * never sees a raw error object or stack trace. The recovery action re-renders
 * the subtree rather than reloading, so surrounding state survives.
 *
 * This is one of the few places a class component is still required: React
 * exposes no hook equivalent of componentDidCatch.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  override state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  override componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Logged for the developer console only. Never rendered, and never sent
    // anywhere that could carry collected content off the client.
    console.error(`Render failed in "${this.props.regionLabel}"`, error, errorInfo.componentStack);
  }

  private readonly handleRetry = (): void => {
    this.setState({ hasError: false });
  };

  override render(): ReactNode {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <div className={styles.container} role="alert">
        <h2 className={styles.heading}>{this.props.regionLabel} could not be displayed</h2>
        <p className={styles.body}>
          Something went wrong while rendering this section. The rest of the page is unaffected.
        </p>
        <button type="button" className={styles.retry} onClick={this.handleRetry}>
          Try again
        </button>
      </div>
    );
  }
}
