import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DpdpService, DPDPPolicy } from '../../services/dpdp.service';

@Component({
  selector: 'app-dpdp-banner',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dpdp-banner.component.html',
  styleUrl: './dpdp-banner.component.scss',
})
export class DpdpBannerComponent implements OnInit {
  visible = false;
  detailsOpen = false;
  policy: DPDPPolicy | null = null;
  loading = false;
  error = '';

  constructor(private dpdp: DpdpService) {}

  ngOnInit(): void {
    this.dpdp.getPolicy().subscribe({
      next: (p) => {
        this.policy = p;
        const local = this.dpdp.getLocalConsent();
        if (!local || local.policy_version !== p.version || !local.consent_given) {
          this.dpdp.fetchStatus().subscribe({
            next: (s: any) => {
              if (!s?.consent_given || s?.needs_renewal) {
                this.visible = true;
              } else {
                this.dpdp.setLocalConsent({
                  consent_given: true,
                  policy_version: s.policy_version,
                  created_at: s.created_at,
                });
              }
            },
            error: () => { this.visible = true; },
          });
        }
      },
      error: () => { this.visible = true; },
    });
  }

  accept(): void { this.submit(true); }
  reject(): void { this.submit(false); }

  toggleDetails(): void { this.detailsOpen = !this.detailsOpen; }

  private submit(consent: boolean): void {
    if (!this.policy) return;
    this.loading = true;
    this.error = '';
    this.dpdp.recordConsent(consent, this.policy.version, this.policy.purposes).subscribe({
      next: () => {
        this.loading = false;
        if (consent) {
          this.dpdp.setLocalConsent({
            consent_given: true,
            policy_version: this.policy!.version,
            created_at: new Date().toISOString(),
          });
          this.visible = false;
        } else {
          this.dpdp.clearLocalConsent();
          this.visible = false;
        }
      },
      error: (err) => {
        this.loading = false;
        this.error = err?.error?.detail || 'Could not record your choice. Please try again.';
      },
    });
  }
}
