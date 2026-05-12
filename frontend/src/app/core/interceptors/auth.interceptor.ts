import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from '../services/auth.service';
import { catchError, throwError } from 'rxjs';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const isAdminReq = req.url.startsWith('/api/admin');
  const token = isAdminReq ? auth.getAdminToken() : auth.getToken();

  const authReq = token
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  return next(authReq).pipe(
    catchError(err => {
      if (err.status === 401) {
        const isAuthReq = req.url.includes('/api/auth/');
        if (!isAuthReq) {
          if (isAdminReq) {
            auth.adminLogout('/admin/login');
          } else {
            auth.logout();
          }
        }
      }
      return throwError(() => err);
    })
  );
};
