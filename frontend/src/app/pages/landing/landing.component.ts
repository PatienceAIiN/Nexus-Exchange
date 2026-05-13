import { Component } from '@angular/core';
import { SupportModalService } from '../../core/services/support-modal.service';

@Component({
  selector: 'app-landing',
  standalone: true,
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.scss'
})
export class LandingComponent {
  constructor(private supportModal: SupportModalService) {}

  openSupport(): void {
    this.supportModal.open();
  }
}
