/**
 * Application Entry Point
 * React DOM rendering with providers
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import App from './App';
import './styles/index.css';

// Create React Query client with configuration
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Refetch data every 30 seconds
      refetchInterval: 30000,
      // Keep data fresh for 20 seconds
      staleTime: 20000,
      // Cache data for 5 minutes
      gcTime: 5 * 60 * 1000,
      // Retry failed requests 3 times
      retry: 3,
      // Show stale data while refetching
      refetchOnWindowFocus: true,
    },
  },
});

// Render application
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <ReactQueryDevtools initialIsOpen={false} position="bottom" />
    </QueryClientProvider>
  </React.StrictMode>
);
