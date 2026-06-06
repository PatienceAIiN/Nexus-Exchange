import { Routes } from '@angular/router';
import { authGuard, adminGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    title: 'Nexus Exchange — Reference Rate Management Platform',
    loadComponent: () => import('./pages/landing/landing.component').then(m => m.LandingComponent),
  },
  {
    path: 'login',
    title: 'Sign in · Nexus Exchange',
    loadComponent: () => import('./pages/login/login.component').then(m => m.LoginComponent),
  },
  {
    path: 'signup',
    title: 'Create account · Nexus Exchange',
    loadComponent: () => import('./pages/signup/signup.component').then(m => m.SignupComponent),
  },
  {
    path: 'dashboard',
    title: 'Dashboard · Nexus Exchange',
    loadComponent: () => import('./pages/dashboard/dashboard.component').then(m => m.DashboardComponent),
    canActivate: [authGuard],
  },
  {
    path: 'admin/login',
    title: 'Admin sign in · Nexus Exchange',
    loadComponent: () => import('./pages/admin-login/admin-login.component').then(m => m.AdminLoginComponent),
  },
  {
    path: 'admin',
    title: 'Admin · Nexus Exchange',
    loadComponent: () => import('./pages/admin/admin.component').then(m => m.AdminComponent),
    canActivate: [adminGuard],
  },
  { path: '**', redirectTo: '/' },
];
