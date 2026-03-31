import { create } from 'zustand';
import type { SchedulerStatus, TaskProgressSnapshot } from '@/types';

interface StatusState {
  status: SchedulerStatus | null;
  setStatus: (s: SchedulerStatus) => void;

  // Live progress snapshots updated from WS events
  applyProgressSnapshot: (taskId: string, snap: TaskProgressSnapshot) => void;
}

const _defaultStatus: SchedulerStatus = {
  running: false,
  is_starting: false,
  is_stopping: false,
  current_task_id: null,
  current_task_name: null,
  progress_snapshot: {},
};

export const useStatusStore = create<StatusState>((set) => ({
  status: _defaultStatus,

  setStatus: (status) => set({ status }),

  applyProgressSnapshot: (taskId, snap) =>
    set((state) => ({
      status: state.status
        ? {
            ...state.status,
            progress_snapshot: {
              ...state.status.progress_snapshot,
              [taskId]: snap,
            },
          }
        : state.status,
    })),
}));
