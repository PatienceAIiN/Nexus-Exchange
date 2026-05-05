import { Injectable, OnDestroy } from '@angular/core';
import { Subject, Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class WebSocketService implements OnDestroy {
  private ws: WebSocket | null = null;
  private messages$ = new Subject<any>();
  private retryDelay = 1000;

  connect(): Observable<any> {
    this.setupWS();
    return this.messages$.asObservable();
  }

  private setupWS(): void {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${proto}//${location.host}/ws/rates`;
    this.ws = new WebSocket(url);

    this.ws.onmessage = (e) => {
      try { this.messages$.next(JSON.parse(e.data)); } catch {}
    };

    this.ws.onclose = () => {
      setTimeout(() => {
        this.retryDelay = Math.min(this.retryDelay * 2, 30000);
        this.setupWS();
      }, this.retryDelay);
    };

    this.ws.onopen = () => { this.retryDelay = 1000; };
  }

  ngOnDestroy(): void {
    this.ws?.close();
  }
}
