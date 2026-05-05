import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { ToastService } from '../../core/services/toast.service';
import { ThemeService } from '../../core/services/theme.service';
import { AuthService } from '../../core/services/auth.service';
import { Toast } from '../../core/models/interfaces';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './admin.component.html',
  styleUrls: ['./admin.component.scss'],
})
export class AdminComponent implements OnInit {
  users: any[] = [];
  stats: any = null;
  loading = false;
  statsLoading = false;
  actionLoading: { [id: number]: string } = {};
  toasts: Toast[] = [];
  isDark = true;
  filterStatus = 'all';
  showDeleteConfirm: number | null = null;
  editingUser: any = null;
  editEmail = '';
  editRole = '';
  editStatus = '';

  constructor(
    private http: HttpClient,
    private toast: ToastService,
    public theme: ThemeService,
    private auth: AuthService
  ) {}

  ngOnInit(): void {
    this.isDark = this.theme.theme$.value === 'dark';
    this.theme.theme$.subscribe(t => this.isDark = t === 'dark');
    this.toast.toasts$.subscribe(t => this.toasts = t);
    this.loadUsers();
    this.loadStats();
  }

  logout(): void {
    this.auth.adminLogout();
  }

  loadUsers(): void {
    this.loading = true;
    this.http.get<any[]>('/api/admin/users').subscribe({
      next: u => { this.users = u; this.loading = false; },
      error: () => { this.loading = false; this.toast.error('Failed to load users'); }
    });
  }

  loadStats(): void {
    this.statsLoading = true;
    this.http.get<any>('/api/admin/stats').subscribe({
      next: s => { this.stats = s; this.statsLoading = false; },
      error: () => { this.statsLoading = false; }
    });
  }

  approve(id: number): void {
    this.actionLoading[id] = 'approving';
    this.http.post(`/api/admin/approve/${id}`, {}).subscribe({
      next: () => { this.toast.success('User approved — email sent'); this.loadUsers(); this.loadStats(); delete this.actionLoading[id]; },
      error: () => { this.toast.error('Failed to approve'); delete this.actionLoading[id]; }
    });
  }

  reject(id: number): void {
    this.actionLoading[id] = 'rejecting';
    this.http.post(`/api/admin/reject/${id}`, {}).subscribe({
      next: () => { this.toast.warning('User rejected'); this.loadUsers(); this.loadStats(); delete this.actionLoading[id]; },
      error: () => { this.toast.error('Failed to reject'); delete this.actionLoading[id]; }
    });
  }

  openEdit(user: any): void {
    this.editingUser = user;
    this.editEmail = user.email || '';
    this.editRole = user.role;
    this.editStatus = user.signup_status;
  }

  saveEdit(): void {
    if (!this.editingUser) return;
    this.actionLoading[this.editingUser.id] = 'editing';
    this.http.put(`/api/admin/users/${this.editingUser.id}`, {
      email: this.editEmail || null,
      role: this.editRole,
      signup_status: this.editStatus,
    }).subscribe({
      next: () => {
        this.toast.success('User updated');
        this.editingUser = null;
        this.loadUsers();
        this.loadStats();
        delete this.actionLoading[this.editingUser?.id];
      },
      error: (e) => {
        this.toast.error(e.error?.detail || 'Update failed');
        delete this.actionLoading[this.editingUser?.id];
      }
    });
  }

  confirmDelete(id: number): void {
    this.showDeleteConfirm = id;
  }

  deleteUser(id: number): void {
    this.actionLoading[id] = 'deleting';
    this.showDeleteConfirm = null;
    this.http.delete(`/api/admin/users/${id}`).subscribe({
      next: () => { this.toast.success('User deleted'); this.loadUsers(); this.loadStats(); delete this.actionLoading[id]; },
      error: (e) => { this.toast.error(e.error?.detail || 'Delete failed'); delete this.actionLoading[id]; }
    });
  }

  get filteredUsers(): any[] {
    if (this.filterStatus === 'all') return this.users;
    return this.users.filter(u => u.signup_status === this.filterStatus);
  }

  get pendingCount(): number { return this.users.filter(u => u.signup_status === 'pending').length; }
  dismissToast(id: number): void { this.toast.dismiss(id); }
}
