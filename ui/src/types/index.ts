// TypeScript types mirroring the Python Pydantic schemas

export type LinkAccountOptions = 'no' | 'google' | 'google_play';
export type EmulatorOptions = 'mumu' | 'mumu_v5' | 'custom';
export type ServerType = 'jp' | 'tw';
export type ControlImpl = 'nemu_ipc' | 'adb' | 'uiautomator';

export type GameCharacter =
  | 'miku' | 'rin' | 'len' | 'luka' | 'meiko' | 'kaito'
  | 'ichika' | 'saki' | 'honami' | 'shiho'
  | 'minori' | 'haruka' | 'airi' | 'shizuku'
  | 'kohane' | 'an' | 'akito' | 'toya'
  | 'tsukasa' | 'emu' | 'nene' | 'rui'
  | 'kanade' | 'mafuyu' | 'ena' | 'mizuki';

export type ChallengeLiveAward =
  | 'crystal' | 'music_card' | 'miracle_gem' | 'magic_cloth' | 'coin' | 'intermediate_practice_score';

export interface CustomEmulatorData {
  adb_ip: string;
  adb_port: number;
  emulator_path: string;
  emulator_args: string;
}

export interface GameConfig {
  server: ServerType;
  link_account: LinkAccountOptions;
  emulator: EmulatorOptions;
  control_impl: ControlImpl;
  check_emulator: boolean;
  emulator_data: CustomEmulatorData | null;
}

export interface LiveConfig {
  enabled: boolean;
  mode: 'auto';
  song_id: number;
  count_mode: 'once' | 'all' | 'specify';
  count: number | null;
  fully_deplete: boolean;
}

export interface ChallengeLiveConfig {
  characters: GameCharacter[];
  award: ChallengeLiveAward;
}

export interface CmConfig {
  watch_ad_wait_sec: number;
}

export interface SchedulerConfig {
  start_game_enabled: boolean;
  solo_live_enabled: boolean;
  challenge_live_enabled: boolean;
  activity_story_enabled: boolean;
  cm_enabled: boolean;
  gift_enabled: boolean;
  area_convos_enabled: boolean;
}

export interface IaaConfig {
  version: number;
  name: string;
  description: string;
  game: GameConfig;
  live: LiveConfig;
  challenge_live: ChallengeLiveConfig;
  cm: CmConfig;
  scheduler: SchedulerConfig;
}

// Progress types
export type ProgressEventType =
  | 'task_started' | 'message' | 'step' | 'task_finished' | 'task_failed';

export type TaskStatus = 'running' | 'finished' | 'failed';

export interface TaskProgressSnapshot {
  run_id: string;
  task_id: string;
  task_name: string;
  timestamp: number;
  status: TaskStatus;
  percent: number | null;
  message: string | null;
  current_steps: number | null;
  total_steps: number | null;
  phase: string | null;
  phase_path: string[] | null;
  error: string | null;
}

export interface ProgressEvent {
  run_id: string;
  task_id: string;
  task_name: string;
  timestamp: number;
  event_type: ProgressEventType;
  payload: Record<string, unknown>;
}

// Scheduler status
export interface SchedulerStatus {
  running: boolean;
  is_starting: boolean;
  is_stopping: boolean;
  current_task_id: string | null;
  current_task_name: string | null;
  progress_snapshot: Record<string, TaskProgressSnapshot>;
}

// Task registry
export interface TaskRegistry {
  regular_tasks: Record<string, string>;
  manual_tasks: Record<string, string>;
}
