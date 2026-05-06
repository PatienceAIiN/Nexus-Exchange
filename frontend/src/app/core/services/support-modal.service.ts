import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class SupportModalService {
  private openSupportSubject = new Subject<void>();
  openSupport$ = this.openSupportSubject.asObservable();

  open(): void {
    this.openSupportSubject.next();
  }
}
