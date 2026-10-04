import { DatePipe } from '@angular/common';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { ApiService } from './api.service';
import { AppEntry, AppStatus, DashboardConfig, StatusMap } from './models';

/** How often the status indicators refresh while the tab is visible. */
const POLL_MS = 30_000;

interface Group {
  name: string | null;
  apps: AppEntry[];
}

@Component({
  selector: 'app-root',
  imports: [DatePipe],
  templateUrl: './app.html',
})
export class App {
  private readonly api = inject(ApiService);
  private readonly pageTitle = inject(Title);

  protected readonly config = signal<DashboardConfig | null>(null);
  protected readonly configError = signal<string | null>(null);
  protected readonly statuses = signal<StatusMap>({});
  protected readonly statusError = signal(false);
  protected readonly checking = signal(false);
  protected readonly lastChecked = signal<Date | null>(null);

  /** Apps grouped in order of first appearance in apps.yaml. */
  protected readonly groups = computed<Group[]>(() => {
    const groups: Group[] = [];
    for (const app of this.config()?.apps ?? []) {
      let group = groups.find((g) => g.name === app.group);
      if (!group) groups.push((group = { name: app.group, apps: [] }));
      group.apps.push(app);
    }
    return groups;
  });

  protected readonly upCount = computed(
    () => this.config()?.apps.filter((a) => this.statuses()[a.id]?.state === 'up').length ?? 0,
  );

  constructor() {
    this.api.apps().subscribe({
      next: (config) => {
        this.config.set(config);
        this.pageTitle.setTitle(config.title);
      },
      error: () => this.configError.set('Die App-Konfiguration konnte nicht geladen werden.'),
    });
    this.refresh();

    const timer = setInterval(() => {
      if (document.visibilityState === 'visible') this.refresh();
    }, POLL_MS);
    // Coming back to a long-hidden tab should not show stale dots.
    const onVisible = () => {
      if (document.visibilityState === 'visible') this.refresh();
    };
    document.addEventListener('visibilitychange', onVisible);
    inject(DestroyRef).onDestroy(() => {
      clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisible);
    });
  }

  protected refresh(): void {
    if (this.checking()) return;
    this.checking.set(true);
    this.api.status().subscribe({
      next: (statuses) => {
        this.statuses.set(statuses);
        this.statusError.set(false);
        this.lastChecked.set(new Date());
        this.checking.set(false);
      },
      error: () => {
        this.statusError.set(true);
        this.checking.set(false);
      },
    });
  }

  protected host(url: string): string {
    return new URL(url).host;
  }

  protected label(status: AppStatus | undefined): string {
    if (!status) return 'Prüfe…';
    switch (status.state) {
      case 'up':
        return `Online · ${status.latency_ms} ms`;
      case 'unhealthy':
        return `Fehler ${status.http_status}`;
      case 'down':
        return status.error === 'timeout' ? 'Timeout' : 'Offline';
    }
  }
}
