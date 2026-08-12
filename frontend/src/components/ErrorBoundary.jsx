import React from 'react';
import { ErrorBoundary as ReactErrorBoundary } from 'react-error-boundary';

function ErrorFallback({ error, resetErrorBoundary }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full bg-white shadow-lg rounded-lg p-6">
        <div className="flex items-center justify-center w-12 h-12 mx-auto bg-red-100 rounded-full">
          <svg
            className="w-6 h-6 text-red-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </div>
        <h2 className="mt-4 text-xl font-semibold text-gray-900 text-center">
          Something went wrong
        </h2>
        <p className="mt-2 text-sm text-gray-600 text-center">
          {error.message || 'An unexpected error occurred'}
        </p>
        <div className="mt-4 p-3 bg-gray-50 rounded border border-gray-200">
          <pre className="text-xs text-gray-700 overflow-auto max-h-32">
            {error.stack}
          </pre>
        </div>
        <button
          type="button"
          onClick={resetErrorBoundary}
          className="mt-6 w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 transition-colors"
        >
          Try again
        </button>
      </div>
    </div>
  );
}

export function ErrorBoundary({ children }) {
  return (
    <ReactErrorBoundary
      FallbackComponent={ErrorFallback}
      onReset={() => {
        // Reset app state
        window.location.href = '/';
      }}
      onError={(error, errorInfo) => {
        // Log to error reporting service
        console.error('Error caught by boundary:', error, errorInfo);
      }}
    >
      {children}
    </ReactErrorBoundary>
  );
}

// Component-level error boundary for smaller sections
export function ComponentErrorBoundary({ children, fallback }) {
  return (
    <ReactErrorBoundary
      fallback={
        fallback || (
          <div className="p-4 bg-red-50 border border-red-200 rounded">
            <p className="text-sm text-red-800">
              Failed to load this component. Please try refreshing the page.
            </p>
          </div>
        )
      }
      onError={(error) => {
        console.error('Component error:', error);
      }}
    >
      {children}
    </ReactErrorBoundary>
  );
}
