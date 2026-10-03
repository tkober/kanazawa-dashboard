export interface AppEntry {
  id: string;
  name: string;
  url: string;
  description: string | null;
  icon: string | null;
  group: string | null;
}

export interface DashboardConfig {
  title: string;
  apps: AppEntry[];
}

export type HealthState = 'up' | 'unhealthy' | 'down';

export interface AppStatus {
  state: HealthState;
  http_status: number | null;
  latency_ms: number | null;
  error: string | null;
  checked_at: number;
}

export type StatusMap = Record<string, AppStatus>;
