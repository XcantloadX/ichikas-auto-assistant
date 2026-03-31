/**
 * React Query hooks wrapping RPC calls.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { wsClient } from '@/ws/client';
import type { IaaConfig, SchedulerStatus, TaskRegistry } from '@/types';

// ── queries ──────────────────────────────────────────────────────────────────

export function useConfig() {
  return useQuery<IaaConfig>({
    queryKey: ['config'],
    queryFn: () => wsClient.call<IaaConfig>('get_config'),
    staleTime: Infinity,
  });
}

export function useStatus() {
  return useQuery<SchedulerStatus>({
    queryKey: ['status'],
    queryFn: () => wsClient.call<SchedulerStatus>('get_status'),
    refetchInterval: 1000,
  });
}

export function useVersion() {
  return useQuery<{ version: string }>({
    queryKey: ['version'],
    queryFn: () => wsClient.call<{ version: string }>('get_version'),
    staleTime: Infinity,
  });
}

export function useTaskRegistry() {
  return useQuery<TaskRegistry>({
    queryKey: ['task_registry'],
    queryFn: () => wsClient.call<TaskRegistry>('get_task_registry'),
    staleTime: Infinity,
  });
}

// ── mutations ─────────────────────────────────────────────────────────────────

export function useSaveConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (config: IaaConfig) =>
      wsClient.call('save_config', { config }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['config'] });
    },
  });
}

export function useStartTasks() {
  return useMutation({
    mutationFn: () => wsClient.call('start_tasks'),
  });
}

export function useStopTasks() {
  return useMutation({
    mutationFn: () => wsClient.call('stop_tasks'),
  });
}

export function useRunSingleTask() {
  return useMutation({
    mutationFn: (taskId: string) => wsClient.call('run_single_task', { task_id: taskId }),
  });
}

export function useExportReport() {
  return useMutation({
    mutationFn: () => wsClient.call<{ path: string }>('export_report'),
  });
}
