import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { SupportModalService } from '../../core/services/support-modal.service';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.scss'
})
export class LandingComponent {
  constructor(private supportModal: SupportModalService) {}

  openSupport(): void {
    this.supportModal.open();
  }
}
