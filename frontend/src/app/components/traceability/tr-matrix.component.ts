import { Component, Input, OnChanges, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  TraceabilityService, Matrix, MatrixRow, CoverageStatus, RequirementType, Priority,
  STATUS_LABELS, STATUS_CLASSES, TYPE_LABELS, saveFile
} from '../../services/traceability.service';

type SortKey = 'reference' | 'priority' | 'status';
const PRIORITY_ORDER: Record<Priority, number> = { haute: 0, moyenne: 1, basse: 2 };
const STATUS_ORDER: Record<CoverageStatus, number> = { non_couverte: 0, partielle: 1, a_verifier: 2, non_analysee: 3, couverte: 4 };

/** Filtre et trie les lignes de la matrice (fonction pure, testée unitairement). */
export function filterMatrixRows(rows: MatrixRow[], search: string, status: CoverageStatus | '', type: RequirementType | '',
                                 priority: Priority | '', sort: SortKey = 'reference'): MatrixRow[] {
  const term = search.trim().toLowerCase();
  return rows
    .filter(r => !status || r.status === status)
    .filter(r => !type || r.type === type)
    .filter(r => !priority || r.priority === priority)
    .filter(r => !term || [r.reference, r.title, r.description, r.justification ?? '', ...r.use_cases.map(u => u.name)]
      .some(value => value.toLowerCase().includes(term)))
    .sort((a, b) => sort === 'priority' ? PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority]
      : sort === 'status' ? STATUS_ORDER[a.status] - STATUS_ORDER[b.status]
      : a.reference.localeCompare(b.reference));
}

@Component({
  selector: 'app-tr-matrix',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div *ngIf="errorMessage" class="mb-6 p-4 border-l-4 border-red-500 bg-red-50 text-red-700 rounded-r-lg font-medium">{{ errorMessage }}</div>

    <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
            <h3 class="text-lg font-black text-gray-800">Matrice de traçabilité</h3>
            <p class="text-sm text-gray-500">Document UML : {{ matrix?.document_name || 'aucun (analysez d\\'abord la traçabilité)' }}</p>
        </div>
        <button type="button" (click)="exportCsv()" [disabled]="!matrix || matrix.rows.length === 0 || isExporting"
            class="px-4 py-2 rounded-xl font-bold text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50">
            {{ isExporting ? 'Export...' : 'Exporter en CSV' }}
        </button>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2 mb-4">
        <input [(ngModel)]="search" name="search" placeholder="Rechercher (réf., titre, cas d'utilisation...)" aria-label="Rechercher"
            class="lg:col-span-2 px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
        <select [(ngModel)]="statusFilter" name="status" aria-label="Filtrer par couverture" class="px-3 py-2 rounded-lg border border-gray-300 bg-white text-sm">
            <option value="">Toutes les couvertures</option>
            <option *ngFor="let s of statuses" [value]="s">{{ statusLabels[s] }}</option>
        </select>
        <select [(ngModel)]="typeFilter" name="type" aria-label="Filtrer par type" class="px-3 py-2 rounded-lg border border-gray-300 bg-white text-sm">
            <option value="">Tous les types</option>
            <option value="fonctionnelle">Fonctionnelle</option>
            <option value="non_fonctionnelle">Non fonctionnelle</option>
        </select>
        <select [(ngModel)]="priorityFilter" name="priority" aria-label="Filtrer par priorité" class="px-3 py-2 rounded-lg border border-gray-300 bg-white text-sm">
            <option value="">Toutes les priorités</option>
            <option value="haute">Haute</option><option value="moyenne">Moyenne</option><option value="basse">Basse</option>
        </select>
    </div>

    <p *ngIf="isLoading" class="text-center text-gray-500">Chargement...</p>
    <p *ngIf="matrix && matrix.rows.length === 0" class="p-6 text-center text-gray-500 bg-gray-50 rounded-2xl">Aucune exigence dans ce projet.</p>

    <div *ngIf="matrix && matrix.rows.length > 0" class="overflow-x-auto rounded-2xl border border-gray-200">
        <table class="min-w-full text-sm bg-white">
            <thead class="bg-gray-50 text-left text-gray-600">
                <tr>
                    <th class="px-3 py-2"><button type="button" (click)="sort = 'reference'" class="font-bold hover:text-indigo-600">Réf. {{ sort === 'reference' ? '↓' : '' }}</button></th>
                    <th class="px-3 py-2">Description</th>
                    <th class="px-3 py-2">Type</th>
                    <th class="px-3 py-2"><button type="button" (click)="sort = 'priority'" class="font-bold hover:text-indigo-600">Priorité {{ sort === 'priority' ? '↓' : '' }}</button></th>
                    <th class="px-3 py-2">Cas d'utilisation associés</th>
                    <th class="px-3 py-2"><button type="button" (click)="sort = 'status'" class="font-bold hover:text-indigo-600">Couverture {{ sort === 'status' ? '↓' : '' }}</button></th>
                    <th class="px-3 py-2">Justification</th>
                </tr>
            </thead>
            <tbody>
                <tr *ngFor="let r of visibleRows" class="border-t border-gray-100 align-top">
                    <td class="px-3 py-2 font-mono font-bold text-indigo-700 whitespace-nowrap">{{ r.reference }}</td>
                    <td class="px-3 py-2 min-w-[14rem]"><p class="font-bold text-gray-800">{{ r.title }}</p><p class="text-gray-500">{{ r.description }}</p></td>
                    <td class="px-3 py-2 whitespace-nowrap">{{ typeLabels[r.type] }}</td>
                    <td class="px-3 py-2">{{ r.priority }}</td>
                    <td class="px-3 py-2">
                        <span *ngFor="let u of r.use_cases" class="inline-block mr-1 mb-1 px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-800 text-xs">{{ u.name }}</span>
                        <span *ngIf="r.use_cases.length === 0" class="text-gray-400">Aucun</span>
                    </td>
                    <td class="px-3 py-2"><span class="px-2 py-0.5 rounded-full text-xs font-bold whitespace-nowrap" [ngClass]="statusClasses[r.status]">{{ statusLabels[r.status] }}</span></td>
                    <td class="px-3 py-2 min-w-[16rem] text-gray-600">
                        {{ r.justification || '—' }}
                        <p *ngIf="r.recommendation" class="mt-1 text-indigo-700">→ {{ r.recommendation }}</p>
                    </td>
                </tr>
            </tbody>
        </table>
        <p class="px-3 py-2 text-xs text-gray-400 bg-gray-50">{{ visibleRows.length }} / {{ matrix.rows.length }} exigence(s) affichée(s)</p>
    </div>
  `
})
export class TrMatrixComponent implements OnChanges {
  private service = inject(TraceabilityService);

  @Input({ required: true }) projectId!: number;

  readonly statusLabels = STATUS_LABELS;
  readonly statusClasses = STATUS_CLASSES;
  readonly typeLabels = TYPE_LABELS;
  readonly statuses = Object.keys(STATUS_LABELS) as CoverageStatus[];

  matrix: Matrix | null = null;
  search = '';
  statusFilter: CoverageStatus | '' = '';
  typeFilter: RequirementType | '' = '';
  priorityFilter: Priority | '' = '';
  sort: SortKey = 'reference';
  isLoading = false;
  isExporting = false;
  errorMessage = '';

  get visibleRows(): MatrixRow[] {
    return this.matrix ? filterMatrixRows(this.matrix.rows, this.search, this.statusFilter, this.typeFilter, this.priorityFilter, this.sort) : [];
  }

  ngOnChanges() {
    this.isLoading = true;
    this.service.getMatrix(this.projectId).subscribe({
      next: matrix => { this.matrix = matrix; this.isLoading = false; },
      error: (err: Error) => { this.errorMessage = err.message; this.isLoading = false; }
    });
  }

  exportCsv() {
    if (!this.matrix) return;
    this.isExporting = true;
    this.service.downloadMatrixCsv(this.projectId, this.matrix.document_id).subscribe({
      next: blob => { saveFile(blob, `matrice-tracabilite-${this.projectId}.csv`); this.isExporting = false; },
      error: (err: Error) => { this.errorMessage = err.message; this.isExporting = false; }
    });
  }
}
