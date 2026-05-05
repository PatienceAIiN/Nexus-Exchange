import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { FBILRate, RatesResponse } from '../models/interfaces';

@Injectable({ providedIn: 'root' })
export class RatesService {
  constructor(private http: HttpClient) {}

  getRates(params: any = {}): Observable<RatesResponse> {
    let p = new HttpParams();
    Object.keys(params).forEach(k => { if (params[k]) p = p.set(k, params[k]); });
    return this.http.get<RatesResponse>('/api/rates', { params: p });
  }

  getLatest(): Observable<FBILRate[]> {
    return this.http.get<FBILRate[]>('/api/rates/latest');
  }

  refresh(): Observable<any> {
    return this.http.post('/api/rates/refresh', {});
  }

  download(params: any): Observable<Blob> {
    let p = new HttpParams();
    Object.keys(params).forEach(k => { if (params[k]) p = p.set(k, params[k]); });
    return this.http.get('/api/rates/download', { params: p, responseType: 'blob' });
  }
}
