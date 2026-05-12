import { Component, ElementRef, HostListener, ViewChild } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.scss'
})
export class LandingComponent {
  @ViewChild('loginDropdown') loginDropdown?: ElementRef<HTMLElement>;

  loginOpen = false;

  toggleLoginMenu(event: MouseEvent): void {
    event.stopPropagation();
    this.loginOpen = !this.loginOpen;
  }

  closeLoginMenu(): void {
    this.loginOpen = false;
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
