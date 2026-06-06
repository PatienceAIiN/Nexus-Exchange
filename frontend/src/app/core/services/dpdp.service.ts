import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

const STORAGE_KEY = 'dpdp_consent_v1';
const VISITOR_KEY = 'dpdp_visitor_id';

export interface DPDPPolicy {
  version: string;
  title: string;
  data_fiduciary: string;
  contact: string;
  purposes: string[];
  categories: string[];
  retention: string;
  rights: string[];
  grievance_officer: string;
}

export interface ConsentRecord {
  consent_given: boolean;
  policy_version: string;
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class DpdpService {
  constructor(private http: HttpClient) {}

  getVisitorId(): string {
    let id = localStorage.getItem(VISITOR_KEY);
    if (!id) {
      id = 'v_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
      localStorage.setItem(VISITOR_KEY, id);
    }
    return id;
  }

  getLocalConsent(): ConsentRecord | null {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    try { return JSON.parse(raw); } catch { return null; }
  }

  setLocalConsent(record: ConsentRecord): void {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(record));
  }

  clearLocalConsent(): void {
    localStorage.removeItem(STORAGE_KEY);
  }

  getPolicy(): Observable<DPDPPolicy> {
    return this.http.get<DPDPPolicy>('/api/dpdp/policy');
  }

  recordConsent(consent_given: boolean, policy_version: string, purposes?: string[]): Observable<any> {
    return this.http.post('/api/dpdp/consent', {
      visitor_id: this.getVisitorId(),
      consent_given,
      policy_version,
      purposes,
    });
  }

  fetchStatus(): Observable<any> {
    const vid = this.getVisitorId();
    return this.http.get(`/api/dpdp/consent/status?visitor_id=${encodeURIComponent(vid)}`);
  }
}
