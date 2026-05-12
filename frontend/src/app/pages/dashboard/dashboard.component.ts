import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { ThemeService } from '../../core/services/theme.service';
import { ToastService } from '../../core/services/toast.service';
import { RatesService } from '../../core/services/rates.service';
import { ProcessingService } from '../../core/services/processing.service';
import { WebSocketService } from '../../core/services/websocket.service';
import { FBILRate, ProcessedFile, ProcessingProgress, Toast } from '../../core/models/interfaces';
import { Subscription } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { SupportModalService } from '../../core/services/support-modal.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss'],
})
export class DashboardComponent implements OnInit, OnDestroy {
  activeTab: 'rates' | 'processing' = 'rates';
  isDark = true;
  user: any = null;
  toasts: Toast[] = [];

  // Rates
  rates: FBILRate[] = [];
  ratesTotalPages = 1;
  ratesPage = 1;
  ratesLoading = false;
  ratesRefreshing = false;
  ratesFromDate = '';
  ratesToDate = '';
  readonly todayDate = new Date().toISOString().split('T')[0];
  ratesCurrency = 'all';
  downloadingFormat = '';
  sortCol = 'date';
  sortDir: 'asc' | 'desc' = 'desc';
  flashedIds = new Set<number>();
  currencies = ['all', 'INR / 1 USD', 'INR / 1 GBP', 'INR / 1 EUR', 'INR / 100 JPY', 'INR / 1 AED', 'INR / 10000 IDR'];

  // Processing
  selectedFile: File | null = null;
  isDragging = false;
  processing = false;
  processResult: ProcessingProgress | null = null;
  progressPercent = 0;
  private progressRaf: any;
  private progressStart = 0;
  showResultModal = false;
  showHistoryModal = false;
  showFileGuideModal = false;
  history: ProcessedFile[] = [];
  historyLoading = false;
  downloadingFileId: number | null = null;
  fileToDelete: ProcessedFile | null = null;
  deletingFile = false;
  
  selectedFileIds = new Set<number>();
  showBulkDeleteConfirm = false;
  deletingBulk = false;

  // Modals
  showChangePassword = false;
  showLogout = false;
  showProfile = false;
  profile: any = null;

  // Change password
  oldPwd = ''; newPwd = ''; confirmPwd = '';
  changingPassword = false;
  pwdError = '';
  showOldPwd = false;
  showNewPwd = false;
  showConfirmPwd = false;

  // Logout
  loggingOut = false;

  private subs = new Subscription();
  private wsSub?: Subscription;

  constructor(
    public auth: AuthService,
    public theme: ThemeService,
    public toastSvc: ToastService,
    private rates$: RatesService,
    private proc: ProcessingService,
    private ws: WebSocketService,
    private http: HttpClient,
    private supportModal: SupportModalService,
  ) {}

  openSupport(): void { this.showProfile = false; this.supportModal.open(); }

  ngOnInit(): void {
    this.user = this.auth.currentUser$.value;
    this.isDark = this.theme.theme$.value === 'dark';
    this.subs.add(this.theme.theme$.subscribe(t => this.isDark = t === 'dark'));
    this.subs.add(this.toastSvc.toasts$.subscribe(t => this.toasts = t));

    const today = new Date(this.todayDate);
    const month = new Date(today.getFullYear(), today.getMonth() - 1, today.getDate());
    this.ratesToDate = this.todayDate;
    this.ratesFromDate = month.toISOString().split('T')[0];

    this.loadRates();
    this.loadProfile();
    this.connectWS();
    this.autoRefreshRatesOnLogin();
  }

  ngOnDestroy(): void {
    this.subs.unsubscribe();
    if (this.progressRaf) cancelAnimationFrame(this.progressRaf);
  }



  private autoRefreshRatesOnLogin(): void {
    const nowUtc = new Date();
    const istNow = new Date(nowUtc.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
    const istDate = istNow.toISOString().split('T')[0];
    const istHour = istNow.getHours();
    const refreshKey = `rates-auto-refresh-${this.user?.id || 'guest'}`;
    const lastAutoRefreshDate = localStorage.getItem(refreshKey);

    if (istHour < 13 || lastAutoRefreshDate === istDate) {
      return;
    }

    this.rates$.refresh().subscribe({
      next: () => {
        localStorage.setItem(refreshKey, istDate);
        this.loadRates();
      },
      error: () => {
        // Keep UX smooth: initial data is still shown from loadRates() even if refresh fails
      }
    });
  }
  loadProfile(): void {
    this.http.get<any>('/api/profile').subscribe({
      next: p => this.profile = p,
      error: () => {}
    });
  }

  connectWS(): void {
    this.wsSub = this.ws.connect().subscribe(msg => {
      if (msg.event === 'rates_updated') {
        this.toastSvc.success('FBIL rates updated in real-time');
        this.loadRates();
      }
    });
    this.subs.add(this.wsSub);
  }

  loadRates(): void {
    this.ratesLoading = true;
    this.rates$.getRates({
      from_date: this.ratesFromDate,
      to_date: this.ratesToDate,
      currency_pair: this.ratesCurrency === 'all' ? '' : this.ratesCurrency,
      page: this.ratesPage,
      per_page: 50,
    }).subscribe({
      next: res => {
        this.rates = res.data;
        this.ratesTotalPages = res.pages;
        this.ratesLoading = false;
      },
      error: () => { this.ratesLoading = false; this.toastSvc.error('Failed to load rates'); }
    });
  }

  onDateFilterChange(): void {
    if (!this.validateAndNormalizeDateRange()) return;
    this.ratesPage = 1;
    this.loadRates();
  }

  onCurrencyChange(): void {
    if (!this.validateAndNormalizeDateRange()) return;
    this.ratesPage = 1;
    this.loadRates();
  }

  private validateAndNormalizeDateRange(): boolean {
    if (!this.ratesFromDate || !this.ratesToDate) return true;

    if (this.ratesFromDate > this.todayDate) {
      this.ratesFromDate = this.todayDate;
      this.toastSvc.error('Start date cannot be in the future.');
      return false;
    }

    if (this.ratesToDate > this.todayDate) {
      this.ratesToDate = this.todayDate;
      this.toastSvc.error('End date cannot be in the future.');
      return false;
    }

    if (this.ratesFromDate > this.ratesToDate) {
      this.toastSvc.error('Invalid range: start date must be before or equal to end date.');
      return false;
    }

    return true;
  }

  refreshRates(): void {
    this.ratesRefreshing = true;
    this.rates$.refresh().subscribe({
      next: (res) => {
        this.ratesRefreshing = false;
        this.toastSvc.success(res.message || 'Rates refreshed');
        this.loadRates();
      },
      error: (e) => {
        this.ratesRefreshing = false;
        this.toastSvc.error(e.error?.detail || 'Refresh failed');
      }
    });
  }

  downloadRates(format: string): void {
    this.downloadingFormat = format;
    this.rates$.download({ from_date: this.ratesFromDate, to_date: this.ratesToDate, format }).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = `fbil_rates.${format}`; a.click();
        URL.revokeObjectURL(url);
        this.downloadingFormat = '';
      },
      error: () => { this.downloadingFormat = ''; this.toastSvc.error('Download failed'); }
    });
  }

  sort(col: string): void {
    if (this.sortCol === col) this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc';
    else { this.sortCol = col; this.sortDir = 'asc'; }
    this.rates.sort((a: any, b: any) => {
      const v = a[col] < b[col] ? -1 : a[col] > b[col] ? 1 : 0;
      return this.sortDir === 'asc' ? v : -v;
    });
  }

  prevPage(): void { if (this.ratesPage > 1) { this.ratesPage--; this.loadRates(); } }
  nextPage(): void { if (this.ratesPage < this.ratesTotalPages) { this.ratesPage++; this.loadRates(); } }

  // File upload
  onDragOver(e: DragEvent): void { e.preventDefault(); this.isDragging = true; }
  onDragLeave(): void { this.isDragging = false; }
  onDrop(e: DragEvent): void {
    e.preventDefault(); this.isDragging = false;
    const file = e.dataTransfer?.files[0];
    if (file) this.setFile(file);
  }
  onFileSelect(e: Event): void {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (file) this.setFile(file);
  }
  setFile(file: File): void {
    if (!file.name.match(/\.(xlsx|csv)$/i)) { this.toastSvc.error('Only .xlsx and .csv files accepted'); return; }
    this.selectedFile = file;
  }
  clearFile(): void { this.selectedFile = null; }

  processFile(): void {
    if (!this.selectedFile) return;
    this.processing = true;
    this.progressPercent = 0;
    this.progressStart = performance.now();
    this.animateProgress();

    this.proc.uploadFile(this.selectedFile).subscribe({
      next: (res) => {
        this.finishProgress(() => {
          this.processing = false;
          this.processResult = res;
          this.showResultModal = true;
          this.toastSvc.success('File processed successfully!');
        });
      },
      error: (e) => {
        if (this.progressRaf) cancelAnimationFrame(this.progressRaf);
        this.processing = false;
        this.progressPercent = 0;
        this.toastSvc.error(e.error?.detail || 'Processing failed');
      }
    });
  }

  private animateProgress(): void {
    const tick = () => {
      const elapsed = (performance.now() - this.progressStart) / 1000;
      // Asymptotic curve: fast start → slows down, max 88%
      this.progressPercent = Math.min(88, Math.round(88 * (1 - Math.exp(-elapsed / 4))));
      if (this.processing && this.progressPercent < 88) {
        this.progressRaf = requestAnimationFrame(tick);
      }
    };
    this.progressRaf = requestAnimationFrame(tick);
  }

  private finishProgress(onDone: () => void): void {
    if (this.progressRaf) cancelAnimationFrame(this.progressRaf);
    const step = () => {
      this.progressPercent = Math.min(100, this.progressPercent + 3);
      if (this.progressPercent < 100) {
        requestAnimationFrame(step);
      } else {
        setTimeout(onDone, 300);
      }
    };
    requestAnimationFrame(step);
  }

  downloadResult(): void {
    if (!this.processResult?.file_id) return;
    this.proc.downloadFile(this.processResult.file_id).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = `processed_file.xlsx`; a.click();
        URL.revokeObjectURL(url);
      },
      error: () => this.toastSvc.error('Download failed')
    });
  }

  openHistory(): void {
    this.showHistoryModal = true;
    this.historyLoading = true;
    this.proc.getHistory().subscribe({
      next: h => { this.history = h; this.historyLoading = false; },
      error: () => { this.historyLoading = false; this.toastSvc.error('Failed to load history'); }
    });
  }

  downloadHistoryFile(file: ProcessedFile): void {
    this.downloadingFileId = file.id;
    this.proc.downloadFile(file.id).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = file.processed_filename; a.click();
        URL.revokeObjectURL(url);
        this.downloadingFileId = null;
      },
      error: () => { this.downloadingFileId = null; this.toastSvc.error('Download failed'); }
    });
  }

  confirmDeleteFile(file: ProcessedFile): void {
    this.fileToDelete = file;
  }

  deleteFile(): void {
    if (!this.fileToDelete) return;
    this.deletingFile = true;
    this.proc.deleteFile(this.fileToDelete.id).subscribe({
      next: () => {
        this.deletingFile = false;
        this.toastSvc.success('File deleted successfully');
        this.history = this.history.filter(f => f.id !== this.fileToDelete!.id);
        this.selectedFileIds.delete(this.fileToDelete!.id);
        this.fileToDelete = null;
      },
      error: () => {
        this.deletingFile = false;
        this.toastSvc.error('Failed to delete file');
      }
    });
  }

  toggleFileSelection(id: number, event: any): void {
    if (event.target.checked) this.selectedFileIds.add(id);
    else this.selectedFileIds.delete(id);
  }

  isAllFilesSelected(): boolean {
    return this.history.length > 0 && this.selectedFileIds.size === this.history.length;
  }

  toggleAllFiles(event: any): void {
    if (event.target.checked) {
      this.history.forEach(f => this.selectedFileIds.add(f.id));
    } else {
      this.selectedFileIds.clear();
    }
  }

  confirmBulkDelete(): void {
    this.showBulkDeleteConfirm = true;
  }

  deleteBulkFiles(): void {
    if (this.selectedFileIds.size === 0) return;
    this.deletingBulk = true;
    this.proc.deleteFilesBulk(Array.from(this.selectedFileIds)).subscribe({
      next: (res) => {
        this.deletingBulk = false;
        this.toastSvc.success(res.message || 'Files deleted successfully');
        this.history = this.history.filter(f => !this.selectedFileIds.has(f.id));
        this.selectedFileIds.clear();
        this.showBulkDeleteConfirm = false;
      },
      error: () => {
        this.deletingBulk = false;
        this.toastSvc.error('Failed to delete files');
      }
    });
  }

  submitChangePassword(): void {
    if (!this.oldPwd || !this.newPwd) { this.pwdError = 'Fill all fields'; return; }
    if (this.newPwd !== this.confirmPwd) { this.pwdError = 'Passwords do not match'; return; }
    if (this.newPwd.length < 6) { this.pwdError = 'Minimum 6 characters'; return; }
    this.changingPassword = true; this.pwdError = '';
    this.auth.changePassword(this.oldPwd, this.newPwd).subscribe({
      next: () => {
        this.changingPassword = false;
        this.toastSvc.success('Password changed. Logging out...');
        this.showChangePassword = false;
        setTimeout(() => this.auth.logout(), 2000);
      },
      error: (e) => { this.changingPassword = false; this.pwdError = e.error?.detail || 'Failed'; }
    });
  }

  confirmLogout(): void {
    this.loggingOut = true;
    setTimeout(() => { this.auth.logout(); }, 500);
  }

  get pwdStrength(): number {
    const p = this.newPwd;
    let s = 0;
    if (p.length >= 6) s++;
    if (p.length >= 10) s++;
    if (/[A-Z]/.test(p)) s++;
    if (/[0-9]/.test(p)) s++;
    if (/[^A-Za-z0-9]/.test(p)) s++;
    return s;
  }

  get pwdStrengthLabel(): string {
    return ['', 'Very Weak', 'Weak', 'Fair', 'Strong', 'Very Strong'][this.pwdStrength] || '';
  }



  formatBytes(bytes: number): string {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  avatarUrl(seed: string | undefined | null): string {
    const s = seed || this.user?.username || 'default';
    return `https://api.dicebear.com/9.x/notionists/svg?seed=${encodeURIComponent(s)}&backgroundColor=b6e3f4,c0aede,d1d4f9,ffd5dc,ffdfbf`;
  }

  dismissToast(id: number): void { this.toastSvc.dismiss(id); }
}
