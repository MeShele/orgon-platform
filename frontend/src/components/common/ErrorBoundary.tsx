"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";
import { Icon } from "@/lib/icons";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Could send to error reporting service
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="flex flex-col items-center justify-center p-8 text-center">
          <Icon icon="solar:danger-triangle-bold" className="text-4xl text-destructive mb-3" />
          <h3 className="text-lg font-semibold text-foreground mb-1">Something went wrong</h3>
          <p className="text-sm text-muted-foreground mb-4">
            {this.state.error?.message || "An unexpected error occurred"}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: undefined })}
            className="px-4 py-2 rounded-lg bg-primary text-white text-sm hover:opacity-90 transition-colors"
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
