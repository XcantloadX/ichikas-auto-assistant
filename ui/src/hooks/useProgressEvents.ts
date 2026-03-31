/**
 * Hook that subscribes to WebSocket progress events and updates the status store.
 */

import { useEffect } from 'react';
import { onProgressEvent } from '@/ws/client';
import { useStatusStore } from '@/stores/useStatusStore';
import type { ProgressEvent, TaskProgressSnapshot } from '@/types';

export function useProgressEvents(): void {
  const applySnapshot = useStatusStore(s => s.applyProgressSnapshot);
  const setStatus = useStatusStore(s => s.setStatus);

  useEffect(() => {
    const unsub = onProgressEvent((event: ProgressEvent) => {
      const p = event.payload as Record<string, unknown>;

      // Build a partial snapshot from the event and merge it in
      const snap: TaskProgressSnapshot = {
        run_id: event.run_id,
        task_id: event.task_id,
        task_name: event.task_name,
        timestamp: event.timestamp,
        status:
          event.event_type === 'task_finished'
            ? 'finished'
            : event.event_type === 'task_failed'
            ? 'failed'
            : 'running',
        percent: (p.percent as number | null) ?? null,
        message: (p.message as string | null) ?? null,
        current_steps: (p.current_steps as number | null) ?? null,
        total_steps: (p.total_steps as number | null) ?? null,
        phase: (p.phase as string | null) ?? null,
        phase_path: (p.phase_path as string[] | null) ?? null,
        error: (p.error as string | null) ?? null,
      };

      applySnapshot(event.task_id, snap);

      // Keep running/stopping flags in sync
      if (event.event_type === 'task_started') {
        setStatus({
          running: true,
          is_starting: false,
          is_stopping: false,
          current_task_id: event.task_id,
          current_task_name: event.task_name,
          progress_snapshot: {},
        });
      } else if (
        event.event_type === 'task_finished' ||
        event.event_type === 'task_failed'
      ) {
        const completedTasks = (p.run_completed_tasks as number) ?? 0;
        const totalTasks = (p.run_total_tasks as number) ?? 1;
        const isLastTask = completedTasks >= totalTasks;
        setStatus({
          running: !isLastTask,
          is_starting: false,
          is_stopping: false,
          current_task_id: isLastTask ? null : event.task_id,
          current_task_name: isLastTask ? null : event.task_name,
          progress_snapshot: {},
        });
      }
    });

    return unsub;
  }, [applySnapshot, setStatus]);
}
