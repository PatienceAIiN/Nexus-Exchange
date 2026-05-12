import { Component, ElementRef, HostListener, ViewChild } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.scss'
})
export class LandingComponent {
  constructor(private readonly router: Router) {}

  @ViewChild('loginDropdown') loginDropdown?: ElementRef<HTMLElement>;

  loginOpen = false;

  toggleLoginMenu(event: MouseEvent): void {
    event.stopPropagation();
    this.loginOpen = !this.loginOpen;
  }

  closeLoginMenu(): void {
    this.loginOpen = false;
  }

  goToClientLogin(): void {
    this.closeLoginMenu();
    this.router.navigate(['/login']);
  }

  goToAdminLogin(): void {
    this.closeLoginMenu();
    this.router.navigate(['/admin/login']);
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!this.loginOpen || !this.loginDropdown) {
      return;
    }

    const target = event.target as Node | null;
    if (target && !this.loginDropdown.nativeElement.contains(target)) {
      this.closeLoginMenu();
    }
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.closeLoginMenu();
  }
}
