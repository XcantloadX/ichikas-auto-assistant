import { create } from 'zustand';
import type { ConnectionStatus } from '@/ws/client';

export type Page = 'main' | 'settings' | 'about';

interface AppState {
  // WebSocket connection status
  wsStatus: ConnectionStatus;
  setWsStatus: (s: ConnectionStatus) => void;

  // Current page
  page: Page;
  setPage: (p: Page) => void;

  // Toast notifications
  toast: { message: string; kind: 'success' | 'error' | 'info' } | null;
  showToast: (message: string, kind?: 'success' | 'error' | 'info') => void;
  clearToast: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  wsStatus: 'connecting',
  setWsStatus: (wsStatus) => set({ wsStatus }),

  page: 'main',
  setPage: (page) => set({ page }),

  toast: null,
  showToast: (message, kind = 'info') => {
    set({ toast: { message, kind } });
    setTimeout(() => set({ toast: null }), 3000);
  },
  clearToast: () => set({ toast: null }),
}));
