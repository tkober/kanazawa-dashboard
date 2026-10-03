import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { DashboardConfig, StatusMap } from './models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);

  apps(): Observable<DashboardConfig> {
    return this.http.get<DashboardConfig>('/api/apps');
  }

  status(): Observable<StatusMap> {
    return this.http.get<StatusMap>('/api/status');
  }
}
