import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { Router } from '@angular/router';
import { TokenResponse } from '../models/interfaces';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly TOKEN_KEY = 'nexus_token';
  private readonly USER_KEY = 'nexus_user';
  private readonly ADMIN_TOKEN_KEY = 'nexus_admin_token';
  private readonly ADMIN_USER_KEY = 'nexus_admin_user';

  isAuthenticated$ = new BehaviorSubject<boolean>(this.hasValidToken());
  currentUser$ = new BehaviorSubject<any>(this.getStoredUser());
  isAdminAuthenticated$ = new BehaviorSubject<boolean>(this.hasValidAdminToken());

  constructor(private http: HttpClient, private router: Router) {}

  login(username: string, password: string): Observable<TokenResponse> {
    return this.http.post<TokenResponse>('/api/auth/login', { username, password }).pipe(
      tap(res => {
        localStorage.setItem(this.TOKEN_KEY, res.access_token);
        localStorage.setItem(this.USER_KEY, JSON.stringify({ username: res.username, role: res.role, id: res.user_id }));
        this.isAuthenticated$.next(true);
        this.currentUser$.next({ username: res.username, role: res.role, id: res.user_id });
      })
    );
  }

  adminLogin(username: string, password: string): Observable<TokenResponse> {
    return this.http.post<TokenResponse>('/api/auth/login', { username, password }).pipe(
      tap(res => {
        if (res.role !== 'admin') {
          throw new Error('Not an admin account');
        }
        // Set admin-specific storage
        localStorage.setItem(this.ADMIN_TOKEN_KEY, res.access_token);
        localStorage.setItem(this.ADMIN_USER_KEY, JSON.stringify({ username: res.username, role: res.role, id: res.user_id }));
        this.isAdminAuthenticated$.next(true);

        // Also set standard user storage so admin can use client dashboard features
        localStorage.setItem(this.TOKEN_KEY, res.access_token);
        localStorage.setItem(this.USER_KEY, JSON.stringify({ username: res.username, role: res.role, id: res.user_id }));
        this.isAuthenticated$.next(true);
        this.currentUser$.next({ username: res.username, role: res.role, id: res.user_id });
      })
    );
  }

  signup(username: string, password: string, email?: string): Observable<any> {
    return this.http.post('/api/auth/signup', { username, password, ...(email ? { email } : {}) });
  }

  changePassword(old_password: string, new_password: string): Observable<any> {
    return this.http.post('/api/auth/change-password', { old_password, new_password });
  }

  logout(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
    this.isAuthenticated$.next(false);
    this.currentUser$.next(null);
    this.router.navigate(['/login']);
  }

  adminLogout(): void {
    localStorage.removeItem(this.ADMIN_TOKEN_KEY);
    localStorage.removeItem(this.ADMIN_USER_KEY);
    this.isAdminAuthenticated$.next(false);
    this.router.navigate(['/admin/login']);
  }

  getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  getAdminToken(): string | null {
    return localStorage.getItem(this.ADMIN_TOKEN_KEY);
  }

  isAuthenticated(): boolean {
    return this.hasValidToken();
  }

  isAdmin(): boolean {
    const user = this.getStoredUser();
    return user?.role === 'admin';
  }

  private hasValidToken(): boolean {
    const token = localStorage.getItem(this.TOKEN_KEY);
    return this.isTokenValid(token);
  }

  private hasValidAdminToken(): boolean {
    const token = localStorage.getItem(this.ADMIN_TOKEN_KEY);
    return this.isTokenValid(token);
  }

  private isTokenValid(token: string | null): boolean {
    if (!token) return false;
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.exp > Date.now() / 1000;
    } catch { return false; }
  }

  private getStoredUser(): any {
    try {
      const s = localStorage.getItem(this.USER_KEY);
      return s ? JSON.parse(s) : null;
    } catch { return null; }
  }
}
