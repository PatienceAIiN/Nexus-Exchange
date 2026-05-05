import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly KEY = 'nexus_theme';
  theme$ = new BehaviorSubject<'dark' | 'light'>(this.getSaved());

  constructor() {
    this.apply(this.theme$.value);
  }

  toggle(): void {
    const next = this.theme$.value === 'dark' ? 'light' : 'dark';
    this.theme$.next(next);
    localStorage.setItem(this.KEY, next);
    this.apply(next);
  }

  private apply(theme: string): void {
    document.documentElement.setAttribute('data-theme', theme);
  }

  private getSaved(): 'dark' | 'light' {
    return (localStorage.getItem(this.KEY) as 'dark' | 'light') || 'dark';
  }
}
