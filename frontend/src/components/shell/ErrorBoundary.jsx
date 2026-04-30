import { Component } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('SecuriSphere ErrorBoundary caught:', error, info);
  }

  reset = () => this.setState({ error: null });

  reload = () => {
    try { window.location.reload(); } catch { /* ignore */ }
  };

  render() {
    if (!this.state.error) return this.props.children;

    const message = this.state.error?.message || String(this.state.error || 'Unknown error');

    return (
      <div className="flex min-h-screen items-center justify-center bg-base-950 px-5">
        <div className="w-full max-w-md rounded-2xl border border-base-800 bg-base-900 p-7 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl border border-red-500/40 bg-red-500/10">
            <AlertTriangle className="h-6 w-6 text-red-300" />
          </div>
          <h1 className="text-lg font-semibold text-base-100 tracking-tight">Something went wrong</h1>
          <p className="mt-1 text-xs text-base-500">
            The dashboard hit an unexpected error. Try a reset, or reload the page if it persists.
          </p>

          <pre className="mt-4 max-h-40 overflow-auto rounded-lg border border-base-800 bg-base-950/60 p-3 text-left font-mono text-[11px] text-red-200/90">
            {message}
          </pre>

          <div className="mt-5 flex justify-center gap-2">
            <button
              onClick={this.reset}
              className="h-9 rounded-lg border border-base-800 bg-base-950/40 px-4 text-xs font-medium text-base-200 hover:bg-base-800 transition-colors"
            >
              Try again
            </button>
            <button
              onClick={this.reload}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-accent px-4 text-xs font-semibold text-base-950 hover:bg-accent-hover transition-colors"
            >
              <RefreshCw className="h-3.5 w-3.5" /> Reload
            </button>
          </div>
        </div>
      </div>
    );
  }
}
