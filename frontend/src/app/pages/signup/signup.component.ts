import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-signup',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './signup.component.html',
  styleUrls: ['./signup.component.scss'],
})
export class SignupComponent {
  username = '';
  password = '';
  confirmPassword = '';
  showPassword = false;
  showConfirmPassword = false;
  email = '';
  loading = false;
  error = '';
  success = false;

  constructor(private auth: AuthService) {}

  submit(): void {
    if (!this.username || !this.password) { this.error = 'Please fill all fields'; return; }
    if (this.password !== this.confirmPassword) { this.error = 'Passwords do not match'; return; }
    if (this.password.length < 6) { this.error = 'Password must be at least 6 characters'; return; }
    this.loading = true;
    this.error = '';
    this.auth.signup(this.username, this.password, this.email || undefined).subscribe({
      next: () => { this.loading = false; this.success = true; },
      error: (e) => { this.loading = false; this.error = e.error?.detail || 'Signup failed'; }
    });
  }
}
