import { Routes } from '@angular/router';
import { authGuard, adminGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    title: 'Xchange Book — Reference Rate Management Platform',
    loadComponent: () => import('./pages/landing/landing.component').then(m => m.LandingComponent),
  },
  {
    path: 'login',
    title: 'Sign in · Xchange Book',
    loadComponent: () => import('./pages/login/login.component').then(m => m.LoginComponent),
  },
  {
    path: 'signup',
    title: 'Create account · Xchange Book',
    loadComponent: () => import('./pages/signup/signup.component').then(m => m.SignupComponent),
  },
  {
    path: 'dashboard',
    title: 'Dashboard · Xchange Book',
    loadComponent: () => import('./pages/dashboard/dashboard.component').then(m => m.DashboardComponent),
    canActivate: [authGuard],
  },
  {
    path: 'admin/login',
    title: 'Admin sign in · Xchange Book',
    loadComponent: () => import('./pages/admin-login/admin-login.component').then(m => m.AdminLoginComponent),
  },
  {
    path: 'admin',
    title: 'Admin · Xchange Book',
    loadComponent: () => import('./pages/admin/admin.component').then(m => m.AdminComponent),
    canActivate: [adminGuard],
  },
  { path: '**', redirectTo: '/' },
];
