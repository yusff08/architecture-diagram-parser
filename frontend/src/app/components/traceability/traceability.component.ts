import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TraceabilityService, Project } from '../../services/traceability.service';
import { TrDashboardComponent } from './tr-dashboard.component';
import { TrRequirementsComponent } from './tr-requirements.component';
import { TrAnalysisComponent } from './tr-analysis.component';
import { TrMatrixComponent } from './tr-matrix.component';
import { TrReportComponent } from './tr-report.component';

export type TrView = 'dashboard' | 'requirements' | 'analysis' | 'matrix' | 'report';

const VIEW_KEY = 'uml-analyzer.traceability.view';
const PROJECT_KEY = 'uml-analyzer.traceability.project';

@Component({
  selector: 'app-traceability',
  standalone: true,
  imports: [CommonModule, FormsModule, TrDashboardComponent, TrRequirementsComponent, TrAnalysisComponent, TrMatrixComponent, TrReportComponent],
  template: `
    <div class="max-w-6xl mx-auto mt-10 p-4 sm:p-8 bg-white/70 backdrop-blur-xl rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.08)] border border-gray-100">

        <div class="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-6 print:hidden">
            <div>
                <h2 class="text-3xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-500">
                    Exigences & Traçabilité
                </h2>
                <p class="text-gray-500 mt-2 font-medium">Extrayez les exigences d'un cahier des charges et vérifiez leur couverture par le diagramme UML.</p>
            </div>
            <div class="w-full md:w-72">
                <label for="tr-project" class="block text-sm font-bold text-gray-700 mb-1">Projet d'analyse</label>
                <select id="tr-project" [ngModel]="projectId" (ngModelChange)="selectProject($event)"
                    class="w-full px-4 py-2 rounded-xl border border-gray-300 bg-white font-medium text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500">
                    <option [ngValue]="null">— Aucun projet sélectionné —</option>
                    <option *ngFor="let p of projects" [ngValue]="p.id">{{ p.name }} ({{ p.requirements_count }} exig.)</option>
                </select>
            </div>
        </div>

        <nav class="flex flex-wrap gap-1 p-1 mb-8 bg-gray-100 rounded-2xl print:hidden">
            <button *ngFor="let v of views" type="button" (click)="setView(v.id)"
                class="flex-1 min-w-[8rem] px-3 py-2 rounded-xl text-sm font-bold transition-all"
                [ngClass]="view === v.id ? 'bg-white text-indigo-700 shadow' : 'text-gray-600 hover:text-indigo-600'">
                {{ v.label }}
            </button>
        </nav>

        <div *ngIf="errorMessage" class="mb-6 p-4 border-l-4 border-red-500 bg-red-50 text-red-700 rounded-r-lg font-medium">
            {{ errorMessage }}
        </div>

        <app-tr-dashboard *ngIf="view === 'dashboard'"
            (newAnalysis)="startNewAnalysis()" (openProject)="openProject($event.id, $event.view)"
            (projectsChanged)="loadProjects()"></app-tr-dashboard>

        <ng-container *ngIf="view !== 'dashboard'">
            <app-tr-requirements *ngIf="view === 'requirements'" [projectId]="projectId"
                (projectSaved)="onProjectSaved($event)" (goTo)="setView($event)"></app-tr-requirements>

            <div *ngIf="view !== 'requirements' && projectId === null" class="p-8 text-center bg-gray-50 rounded-2xl border border-dashed border-gray-300">
                <p class="text-gray-600 font-medium">Sélectionnez un projet ci-dessus ou créez-en un pour continuer.</p>
                <button type="button" (click)="startNewAnalysis()"
                    class="mt-4 px-5 py-2 rounded-xl font-bold text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500">
                    + Nouvelle analyse
                </button>
            </div>

            <ng-container *ngIf="projectId !== null">
                <app-tr-analysis *ngIf="view === 'analysis'" [projectId]="projectId" (goTo)="setView($event)"></app-tr-analysis>
                <app-tr-matrix *ngIf="view === 'matrix'" [projectId]="projectId"></app-tr-matrix>
                <app-tr-report *ngIf="view === 'report'" [projectId]="projectId"></app-tr-report>
            </ng-container>
        </ng-container>
    </div>
  `
})
export class TraceabilityComponent implements OnInit {
  private service = inject(TraceabilityService);

  readonly views: { id: TrView; label: string }[] = [
    { id: 'dashboard', label: '1. Tableau de bord' },
    { id: 'requirements', label: '2. Exigences' },
    { id: 'analysis', label: '3. Traçabilité' },
    { id: 'matrix', label: '4. Matrice' },
    { id: 'report', label: '5. Rapport' }
  ];

  projects: Project[] = [];
  projectId: number | null = null;
  view: TrView = 'dashboard';
  errorMessage = '';

  ngOnInit() {
    this.view = (readStorage(VIEW_KEY) as TrView) || 'dashboard';
    if (!this.views.some(v => v.id === this.view)) this.view = 'dashboard';
    const stored = Number(readStorage(PROJECT_KEY));
    this.projectId = stored > 0 ? stored : null;
    this.loadProjects();
  }

  loadProjects() {
    this.service.getProjects().subscribe({
      next: projects => {
        this.projects = projects;
        this.errorMessage = '';
        if (this.projectId !== null && !projects.some(p => p.id === this.projectId)) {
          this.selectProject(null);
        }
      },
      error: (err: Error) => this.errorMessage = err.message
    });
  }

  selectProject(id: number | null) {
    this.projectId = id;
    writeStorage(PROJECT_KEY, id === null ? '' : String(id));
  }

  setView(view: TrView) {
    this.view = view;
    writeStorage(VIEW_KEY, view);
  }

  startNewAnalysis() {
    this.selectProject(null);
    this.setView('requirements');
  }

  openProject(id: number, view: TrView) {
    this.selectProject(id);
    this.setView(view);
  }

  onProjectSaved(project: Project) {
    this.selectProject(project.id);
    this.loadProjects();
  }
}

// Préférences d'affichage uniquement : l'application fonctionne sans stockage local
function readStorage(key: string): string | null {
  try { return localStorage.getItem(key); } catch { return null; }
}

function writeStorage(key: string, value: string) {
  try { localStorage.setItem(key, value); } catch { /* ignoré */ }
}
