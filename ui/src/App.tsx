import { useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Global } from '@emotion/react';
import { AppShell } from '@/components/layout/AppShell';
import { MainPage } from '@/components/pages/MainPage';
import { SettingsPage } from '@/components/pages/SettingsPage';
import { AboutPage } from '@/components/pages/AboutPage';
import { Toast } from '@/components/ui/Toast';
import { useAppStore } from '@/stores/useAppStore';
import { useProgressEvents } from '@/hooks/useProgressEvents';
import { wsClient } from '@/ws/client';
import globalStyles from '@/styles/global.scss?inline';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function AppInner() {
  const { page, setWsStatus } = useAppStore();
  useProgressEvents();

  useEffect(() => {
    wsClient.connect();
    const unsub = wsClient.onStatusChange(setWsStatus);
    return () => {
      unsub();
      wsClient.disconnect();
    };
  }, [setWsStatus]);

  return (
    <AppShell>
      {page === 'main' && <MainPage />}
      {page === 'settings' && <SettingsPage />}
      {page === 'about' && <AboutPage />}
      <Toast />
    </AppShell>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Global styles={globalStyles} />
      <AppInner />
    </QueryClientProvider>
  );
}
