import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { AuthService } from './core/services/auth.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent {
  title = 'frontend';
  supportOpen = false;
  loading = false;
  success = '';
  error = '';
  form = { username: '', email: '', subject: '', message: '' };

  constructor(private http: HttpClient, private authService: AuthService) {
    const user = this.authService.currentUser$.value;
    if (user?.username) this.form.username = user.username;
  }

  openSupport() { this.supportOpen = true; }
  closeSupport() { this.supportOpen = false; this.success = ''; this.error = ''; }

  submitSupport() {
    this.loading = true;
    this.success = '';
    this.error = '';
    this.http.post('/api/support', this.form).subscribe({
      next: () => {
        this.loading = false;
        this.success = 'Support request submitted.';
        this.form.subject = '';
        this.form.message = '';
      },
      error: (err) => {
        this.loading = false;
        this.error = err?.error?.detail || 'Failed to submit support request';
      }
    });
  }
}
