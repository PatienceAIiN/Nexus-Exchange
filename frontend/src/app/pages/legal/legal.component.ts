import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, ActivatedRoute } from '@angular/router';
import { Subscription } from 'rxjs';

type Doc = 'terms' | 'privacy' | 'data';

@Component({
  selector: 'app-legal',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './legal.component.html',
  styleUrls: ['./legal.component.scss'],
})
export class LegalComponent implements OnInit, OnDestroy {
  doc: Doc = 'terms';
  updated = 'July 2026';
  private sub?: Subscription;

  constructor(private route: ActivatedRoute) {}

  ngOnInit(): void {
    this.sub = this.route.paramMap.subscribe(p => {
      const d = (p.get('doc') || 'terms').toLowerCase();
      this.doc = (['terms', 'privacy', 'data'].includes(d) ? d : 'terms') as Doc;
      if (typeof window !== 'undefined') window.scrollTo(0, 0);
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }
}
