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

  /** App whose tile was just clicked; shows the "opening" overlay while navigation is in flight. */
  protected readonly opening = signal<AppEntry | null>(null);

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
    // Returning via the back button from bfcache must not leave a stuck overlay.
    const onPageShow = (event: PageTransitionEvent) => {
      if (event.persisted) this.opening.set(null);
    };
    window.addEventListener('pageshow', onPageShow);
    // Escape cancels the pending navigation, same as the "Abbrechen" button.
    const onKeydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && this.opening()) this.cancelOpening();
    };
    document.addEventListener('keydown', onKeydown);
    inject(DestroyRef).onDestroy(() => {
      clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisible);
      window.removeEventListener('pageshow', onPageShow);
      document.removeEventListener('keydown', onKeydown);
    });
  }

  protected refresh(): void {
    if (this.checking() || this.opening()) return;
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

  /** Lets a plain left click through to the anchor, but shows the "opening" overlay for it. */
  protected onTileClick(event: MouseEvent, app: AppEntry): void {
    if (this.opening()) {
      // Already navigating; don't let a second click fire another navigation.
      event.preventDefault();
      return;
    }
    const isPlainLeftClick =
      event.button === 0 && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey;
    if (!isPlainLeftClick) return;
    // No preventDefault: the anchor navigates normally, we just overlay on top of it.
    this.opening.set(app);
  }

  /** Cancels the pending navigation (Abbrechen button or Escape key). */
  protected cancelOpening(): void {
    window.stop();
    this.opening.set(null);
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
