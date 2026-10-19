import { Component, Input, OnChanges, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { forkJoin } from 'rxjs';
import {
  TraceabilityService, Matrix, Analysis, Project, CoverageStats, STATUS_LABELS, saveFile
} from '../../services/traceability.service';

export interface ChartSegment {
  label: string;
  value: number;
  percent: number;
  color: string;
}

/** Répartition des exigences par statut, pour le graphique (fonction pure, testée unitairement). */
export function coverageSegments(stats: CoverageStats): ChartSegment[] {
  const raw = [
    { label: STATUS_LABELS.couverte, value: stats.covered, color: '#16a34a' },
    { label: STATUS_LABELS.partielle, value: stats.partial, color: '#f59e0b' },
    { label: STATUS_LABELS.non_couverte, value: stats.uncovered, color: '#dc2626' },
    { label: STATUS_LABELS.a_verifier, value: stats.to_verify, color: '#0284c7' },
    { label: STATUS_LABELS.non_analysee, value: stats.not_analyzed, color: '#9ca3af' }
  ];
  return raw.map(s => ({ ...s, percent: stats.total ? Math.round(s.value / stats.total * 1000) / 10 : 0 }));
}

@Component({
  selector: 'app-tr-report',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div *ngIf="errorMessage" class="mb-6 p-4 border-l-4 border-red-500 bg-red-50 text-red-700 rounded-r-lg font-medium">{{ errorMessage }}</div>
    <p *ngIf="isLoading" class="text-center text-gray-500">Chargement...</p>

    <ng-container *ngIf="matrix && project">
        <div class="flex flex-wrap items-start justify-between gap-3 mb-6">
            <div>
                <h3 class="text-2xl font-black text-gray-800">Rapport de couverture — {{ project.name }}</h3>
                <p class="text-sm text-gray-500">Document UML : {{ matrix.document_name || 'aucun' }}
                    · {{ lastAnalysis ? 'analyse du ' + lastAnalysis.created_at + ' (' + lastAnalysis.model + ')' : 'aucune analyse IA enregistrée' }}</p>
            </div>
            <div class="flex flex-wrap gap-2 print:hidden">
                <button type="button" (click)="exportMarkdown()" [disabled]="isExporting" class="px-4 py-2 rounded-xl font-bold text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50">Exporter en Markdown</button>
                <button type="button" (click)="print()" class="px-4 py-2 rounded-xl font-bold text-indigo-700 bg-indigo-100 hover:bg-indigo-200">Imprimer / PDF</button>
            </div>
        </div>

        <section class="p-5 mb-6 bg-gray-50 rounded-2xl border border-gray-200">
            <h4 class="font-black text-gray-800 mb-2">Résumé de l'analyse</h4>
            <p class="text-sm text-gray-700">{{ lastAnalysis?.summary || 'Aucun résumé : lancez une analyse de traçabilité avec Gemini.' }}</p>
        </section>

        <section class="grid md:grid-cols-2 gap-6 mb-6">
            <div class="p-5 bg-white rounded-2xl border border-gray-200">
                <h4 class="font-black text-gray-800 mb-3">Statistiques</h4>
                <dl class="grid grid-cols-2 gap-y-1 text-sm">
                    <dt class="text-gray-500">Exigences</dt><dd class="font-bold text-right">{{ matrix.stats.total }}</dd>
                    <dt class="text-gray-500">Fonctionnelles</dt><dd class="font-bold text-right">{{ matrix.stats.functional }}</dd>
                    <dt class="text-gray-500">Non fonctionnelles</dt><dd class="font-bold text-right">{{ matrix.stats.non_functional }}</dd>
                    <dt class="text-gray-500">Couvertes</dt><dd class="font-bold text-right text-green-700">{{ matrix.stats.covered }}</dd>
                    <dt class="text-gray-500">Partiellement couvertes</dt><dd class="font-bold text-right text-amber-700">{{ matrix.stats.partial }}</dd>
                    <dt class="text-gray-500">Non couvertes</dt><dd class="font-bold text-right text-red-700">{{ matrix.stats.uncovered }}</dd>
                    <dt class="text-gray-500">À vérifier manuellement</dt><dd class="font-bold text-right text-sky-700">{{ matrix.stats.to_verify }}</dd>
                    <dt class="text-gray-500">Non analysées</dt><dd class="font-bold text-right">{{ matrix.stats.not_analyzed }}</dd>
                </dl>
                <div class="mt-4 p-3 bg-indigo-50 rounded-xl">
                    <p class="text-sm font-bold text-indigo-800">Taux de couverture :
                        <span class="text-2xl font-black">{{ matrix.stats.coverage_rate !== null ? matrix.stats.coverage_rate + ' %' : 'non calculable' }}</span></p>
                    <p class="text-xs text-indigo-700 mt-1">Formule : {{ matrix.stats.formula }}</p>
                    <p class="text-xs text-indigo-700">Dénominateur : {{ matrix.stats.analyzable_functional }} exigence(s) fonctionnelle(s) analysable(s).
                        Les exigences à vérifier, non analysées et non fonctionnelles sont comptées à part.</p>
                </div>
            </div>

            <div class="p-5 bg-white rounded-2xl border border-gray-200">
                <h4 class="font-black text-gray-800 mb-3">Répartition des exigences</h4>
                <p *ngIf="matrix.stats.total === 0" class="text-sm text-gray-400">Aucune exigence.</p>
                <ng-container *ngIf="matrix.stats.total > 0">
                    <div class="flex h-6 w-full rounded-full overflow-hidden bg-gray-100" role="img"
                        [attr.aria-label]="chartLabel">
                        <div *ngFor="let s of segments" [style.width.%]="s.percent" [style.background-color]="s.color" [title]="s.label + ' : ' + s.value"></div>
                    </div>
                    <ul class="mt-4 space-y-2">
                        <li *ngFor="let s of segments" class="flex items-center gap-2 text-sm">
                            <span class="inline-block w-3 h-3 rounded-sm" [style.background-color]="s.color"></span>
                            <span class="flex-1 text-gray-700">{{ s.label }}</span>
                            <span class="font-bold text-gray-800">{{ s.value }}</span>
                            <span class="w-14 text-right text-gray-500">{{ s.percent }} %</span>
                        </li>
                    </ul>
                </ng-container>
            </div>
        </section>

        <section class="p-5 mb-6 bg-white rounded-2xl border border-gray-200">
            <h4 class="font-black text-gray-800 mb-3">Exigences manquantes ou partielles ({{ missing.length }})</h4>
            <p *ngIf="missing.length === 0" class="text-sm text-gray-500">Aucune exigence non couverte ou partiellement couverte.</p>
            <ul class="space-y-2">
                <li *ngFor="let r of missing" class="text-sm">
                    <span class="font-mono font-bold text-indigo-700">{{ r.reference }}</span>
                    <span class="font-bold text-gray-800"> {{ r.title }}</span>
                    <span class="text-gray-500"> ({{ statusLabels[r.status] }})</span>
                    <p class="text-indigo-700">→ {{ r.recommendation || 'Aucune recommandation.' }}</p>
                </li>
            </ul>
        </section>

        <section class="p-5 bg-indigo-50/60 rounded-2xl border border-indigo-200">
            <h4 class="font-black text-gray-800 mb-3">Suggestions d'amélioration (IA)</h4>
            <p *ngIf="!lastAnalysis?.suggestions?.length" class="text-sm text-gray-500">Aucune suggestion disponible.</p>
            <ul class="text-sm text-gray-700 space-y-1">
                <li *ngFor="let s of lastAnalysis?.suggestions">→ {{ s }}</li>
            </ul>
            <p class="mt-3 text-xs text-gray-500">Ces suggestions sont des recommandations : le diagramme UML original n'est jamais modifié automatiquement.</p>
        </section>
    </ng-container>
  `
})
export class TrReportComponent implements OnChanges {
  private service = inject(TraceabilityService);

  @Input({ required: true }) projectId!: number;

  readonly statusLabels = STATUS_LABELS;

  project: Project | null = null;
  matrix: Matrix | null = null;
  lastAnalysis: Analysis | null = null;
  segments: ChartSegment[] = [];
  isLoading = false;
  isExporting = false;
  errorMessage = '';

  get missing() {
    return this.matrix?.rows.filter(r => r.status === 'non_couverte' || r.status === 'partielle') ?? [];
  }

  get chartLabel() {
    return 'Répartition : ' + this.segments.map(s => `${s.label} ${s.value}`).join(', ');
  }

  ngOnChanges() {
    this.isLoading = true;
    forkJoin({
      project: this.service.getProject(this.projectId),
      matrix: this.service.getMatrix(this.projectId),
      analyses: this.service.getAnalyses(this.projectId)
    }).subscribe({
      next: ({ project, matrix, analyses }) => {
        this.project = project;
        this.matrix = matrix;
        this.segments = coverageSegments(matrix.stats);
        this.lastAnalysis = analyses.find(a => a.document_id === matrix.document_id) ?? null;
        this.isLoading = false;
      },
      error: (err: Error) => { this.errorMessage = err.message; this.isLoading = false; }
    });
  }

  exportMarkdown() {
    this.isExporting = true;
    this.service.downloadReportMarkdown(this.projectId, this.matrix?.document_id).subscribe({
      next: markdown => {
        saveFile(markdown, `rapport-couverture-${this.projectId}.md`, 'text/markdown;charset=utf-8');
        this.isExporting = false;
      },
      error: (err: Error) => { this.errorMessage = err.message; this.isExporting = false; }
    });
  }

  print() {
    // Aucune dépendance PDF dans le projet : l'impression du navigateur permet d'enregistrer en PDF
    window.print();
  }
}
