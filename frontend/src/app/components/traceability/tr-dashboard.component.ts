import { Component, EventEmitter, OnInit, Output, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TraceabilityService, Dashboard } from '../../services/traceability.service';
import type { TrView } from './traceability.component';

@Component({
  selector: 'app-tr-dashboard',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
        <h3 class="text-xl font-black text-gray-800">Tableau de bord</h3>
        <button type="button" (click)="newAnalysis.emit()"
            class="px-5 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 shadow-[0_4px_14px_0_rgb(99,102,241,0.39)] active:scale-95 transition-all">
            + Nouvelle analyse
        </button>
    </div>

    <div *ngIf="errorMessage" class="mb-6 p-4 border-l-4 border-red-500 bg-red-50 text-red-700 rounded-r-lg font-medium">{{ errorMessage }}</div>
    <p *ngIf="isLoading" class="text-center text-gray-500">Chargement...</p>

    <ng-container *ngIf="data">
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div class="p-5 bg-white rounded-2xl border border-gray-200 shadow-sm">
                <p class="text-sm font-bold text-gray-500">Exigences</p>
                <p class="text-3xl font-black text-gray-800 mt-1">{{ data.totals.total }}</p>
                <p class="text-xs text-gray-400 mt-1">{{ data.totals.functional }} fonct. · {{ data.totals.non_functional }} non fonct.</p>
            </div>
            <div class="p-5 bg-white rounded-2xl border border-gray-200 shadow-sm">
                <p class="text-sm font-bold text-gray-500">Couvertes</p>
                <p class="text-3xl font-black text-green-600 mt-1">{{ data.totals.covered }}</p>
                <p class="text-xs text-gray-400 mt-1">+ {{ data.totals.partial }} partiellement</p>
            </div>
            <div class="p-5 bg-white rounded-2xl border border-gray-200 shadow-sm">
                <p class="text-sm font-bold text-gray-500">Non couvertes</p>
                <p class="text-3xl font-black text-red-600 mt-1">{{ data.totals.uncovered }}</p>
                <p class="text-xs text-gray-400 mt-1">{{ data.totals.to_verify }} à vérifier · {{ data.totals.not_analyzed }} non analysées</p>
            </div>
            <div class="p-5 bg-white rounded-2xl border border-gray-200 shadow-sm">
                <p class="text-sm font-bold text-gray-500">Taux de couverture</p>
                <p class="text-3xl font-black text-indigo-600 mt-1">{{ data.totals.coverage_rate !== null ? data.totals.coverage_rate + ' %' : '—' }}</p>
                <p class="text-xs text-gray-400 mt-1">sur {{ data.totals.analyzable_functional }} exig. fonctionnelle(s) analysable(s)</p>
            </div>
        </div>

        <h4 class="text-lg font-black text-gray-800 mb-3">Projets ({{ data.projects_count }}) · {{ data.analyses_count }} analyse(s) enregistrée(s)</h4>
        <p *ngIf="data.projects.length === 0" class="p-6 text-center text-gray-500 bg-gray-50 rounded-2xl border border-dashed border-gray-300">
            Aucun projet pour le moment. Cliquez sur « Nouvelle analyse » pour commencer.
        </p>

        <div class="space-y-3 mb-8">
            <div *ngFor="let p of data.projects" class="p-4 bg-white rounded-2xl border border-gray-200 shadow-sm flex flex-col md:flex-row md:items-center gap-3">
                <div class="flex-1 min-w-0">
                    <p class="font-bold text-gray-800 truncate">{{ p.name }}</p>
                    <p class="text-xs text-gray-500">
                        {{ p.requirements_count }} exigence(s)
                        · {{ p.stats?.coverage_rate != null ? 'couverture ' + p.stats?.coverage_rate + ' %' : 'couverture non calculée' }}
                        · {{ p.last_analysis_at ? 'dernière analyse le ' + p.last_analysis_at : 'jamais analysé' }}
                    </p>
                </div>
                <div *ngIf="confirmDeleteId !== p.id" class="flex flex-wrap gap-2">
                    <button type="button" (click)="openProject.emit({ id: p.id, view: 'requirements' })" class="px-3 py-1.5 text-sm font-bold rounded-lg bg-indigo-100 text-indigo-700 hover:bg-indigo-200">Exigences</button>
                    <button type="button" (click)="openProject.emit({ id: p.id, view: 'analysis' })" class="px-3 py-1.5 text-sm font-bold rounded-lg bg-indigo-100 text-indigo-700 hover:bg-indigo-200">Traçabilité</button>
                    <button type="button" (click)="openProject.emit({ id: p.id, view: 'report' })" class="px-3 py-1.5 text-sm font-bold rounded-lg bg-indigo-100 text-indigo-700 hover:bg-indigo-200">Rapport</button>
                    <button type="button" (click)="confirmDeleteId = p.id" class="px-3 py-1.5 text-sm font-bold rounded-lg bg-red-50 text-red-600 hover:bg-red-100">Supprimer</button>
                </div>
                <div *ngIf="confirmDeleteId === p.id" class="flex flex-wrap items-center gap-2">
                    <span class="text-sm font-medium text-red-700">Supprimer le projet et toutes ses données ?</span>
                    <button type="button" (click)="deleteProject(p.id)" class="px-3 py-1.5 text-sm font-bold rounded-lg bg-red-600 text-white hover:bg-red-500">Confirmer</button>
                    <button type="button" (click)="confirmDeleteId = null" class="px-3 py-1.5 text-sm font-bold rounded-lg bg-gray-200 text-gray-600 hover:bg-gray-300">Annuler</button>
                </div>
            </div>
        </div>

        <h4 class="text-lg font-black text-gray-800 mb-3">Analyses récentes</h4>
        <p *ngIf="data.recent_analyses.length === 0" class="text-sm text-gray-500">Aucune analyse de traçabilité enregistrée.</p>
        <ul class="space-y-2">
            <li *ngFor="let a of data.recent_analyses" class="p-3 bg-gray-50 rounded-xl border border-gray-200 text-sm">
                <button type="button" (click)="openProject.emit({ id: a.project_id, view: 'report' })" class="font-bold text-indigo-700 hover:underline">{{ a.project_name }}</button>
                <span class="text-gray-500"> · {{ a.document_name || 'document supprimé' }} · {{ a.created_at }} · </span>
                <span class="font-bold text-gray-700">{{ a.stats.coverage_rate !== null ? a.stats.coverage_rate + ' %' : 'taux non calculable' }}</span>
            </li>
        </ul>
    </ng-container>
  `
})
export class TrDashboardComponent implements OnInit {
  private service = inject(TraceabilityService);

  @Output() newAnalysis = new EventEmitter<void>();
  @Output() openProject = new EventEmitter<{ id: number; view: TrView }>();
  @Output() projectsChanged = new EventEmitter<void>();

  data: Dashboard | null = null;
  isLoading = false;
  errorMessage = '';
  confirmDeleteId: number | null = null;

  ngOnInit() {
    this.load();
  }

  load() {
    this.isLoading = true;
    this.service.getDashboard().subscribe({
      next: data => { this.data = data; this.isLoading = false; this.errorMessage = ''; },
      error: (err: Error) => { this.errorMessage = err.message; this.isLoading = false; }
    });
  }

  deleteProject(id: number) {
    this.service.deleteProject(id).subscribe({
      next: () => { this.confirmDeleteId = null; this.load(); this.projectsChanged.emit(); },
      error: (err: Error) => this.errorMessage = err.message
    });
  }
}
