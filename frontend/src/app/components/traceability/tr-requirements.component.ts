import { Component, EventEmitter, Input, OnChanges, Output, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Observable, throwError } from 'rxjs';
import { switchMap, tap } from 'rxjs/operators';
import {
  TraceabilityService, Project, Requirement, RequirementDraft, Priority, RequirementType,
  STATUS_LABELS, STATUS_CLASSES, TYPE_LABELS
} from '../../services/traceability.service';
import type { TrView } from './traceability.component';

const MAX_FILE_SIZE = 1024 * 1024;
const MAX_SPEC_CHARS = 50000;

@Component({
  selector: 'app-tr-requirements',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div *ngIf="errorMessage" class="mb-6 p-4 border-l-4 border-red-500 bg-red-50 text-red-700 rounded-r-lg font-medium">{{ errorMessage }}</div>
    <div *ngIf="successMessage" class="mb-6 p-4 border-l-4 border-green-500 bg-green-50 text-green-700 rounded-r-lg font-medium">{{ successMessage }}</div>

    <!-- Projet -->
    <section class="p-6 mb-8 bg-gray-50 rounded-2xl border border-gray-200 space-y-4">
        <h3 class="text-lg font-black text-gray-800">{{ project ? 'Projet : ' + project.name : 'Nouveau projet d\\'analyse' }}</h3>
        <div class="grid md:grid-cols-2 gap-4">
            <div>
                <label for="tr-p-name" class="block text-sm font-bold text-gray-700 mb-1">Nom du projet *</label>
                <input id="tr-p-name" [(ngModel)]="projectForm.name" name="projectName" maxlength="100" placeholder="Ex : Réservation en ligne"
                    class="w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500">
            </div>
            <div>
                <label for="tr-p-desc" class="block text-sm font-bold text-gray-700 mb-1">Description</label>
                <input id="tr-p-desc" [(ngModel)]="projectForm.description" name="projectDescription" maxlength="500"
                    class="w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500">
            </div>
        </div>

        <div>
            <div class="flex flex-wrap items-center justify-between gap-2 mb-1">
                <label for="tr-spec" class="block text-sm font-bold text-gray-700">Cahier des charges</label>
                <div class="flex items-center gap-2">
                    <input #specFile type="file" class="hidden" accept=".txt,.md,.markdown,text/plain,text/markdown" (change)="importSpecification($event)">
                    <button type="button" (click)="specFile.click()" [disabled]="isBusy"
                        class="px-3 py-1.5 text-sm font-bold rounded-lg bg-indigo-100 text-indigo-700 hover:bg-indigo-200 disabled:opacity-50">
                        Importer un fichier (.txt, .md)
                    </button>
                </div>
            </div>
            <textarea id="tr-spec" [(ngModel)]="specText" name="spec" rows="7" [attr.maxlength]="maxSpecChars"
                placeholder="Ex : Le client doit pouvoir se connecter, consulter son profil et effectuer une réservation. L'administrateur doit pouvoir gérer les utilisateurs. Le système doit répondre rapidement aux requêtes."
                class="w-full px-4 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"></textarea>
            <p class="mt-1 text-xs text-gray-400">{{ specText.length }} / {{ maxSpecChars }} caractères (minimum 20 pour l'extraction).</p>
        </div>

        <div class="flex flex-wrap gap-3">
            <button type="button" (click)="extract()" [disabled]="isBusy || specText.trim().length < 20"
                class="flex items-center gap-2 px-5 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 shadow-[0_4px_14px_0_rgb(99,102,241,0.39)] disabled:opacity-50 disabled:shadow-none">
                <svg *ngIf="isExtracting" class="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
                {{ isExtracting ? 'Extraction en cours (Gemini)...' : 'Extraire les exigences avec IA' }}
            </button>
            <button type="button" (click)="saveProject()" [disabled]="isBusy"
                class="px-5 py-3 rounded-xl font-bold text-indigo-700 bg-indigo-100 hover:bg-indigo-200 disabled:opacity-50">
                {{ project ? 'Enregistrer le projet' : 'Créer le projet' }}
            </button>
        </div>
    </section>

    <!-- Exigences proposées (à valider) -->
    <section *ngIf="drafts.length > 0" class="p-6 mb-8 bg-indigo-50/60 rounded-2xl border border-indigo-200">
        <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
            <div>
                <h3 class="text-lg font-black text-gray-800">Exigences proposées ({{ drafts.length }})</h3>
                <p class="text-sm text-gray-600">Source : {{ draftSource }}. Vérifiez et corrigez avant d'enregistrer.</p>
            </div>
            <button type="button" (click)="addDraft()" class="px-3 py-1.5 text-sm font-bold rounded-lg bg-white text-indigo-700 border border-indigo-200 hover:bg-indigo-100">+ Ajouter une ligne</button>
        </div>

        <div class="space-y-3">
            <div *ngFor="let d of drafts; let i = index" class="grid grid-cols-1 md:grid-cols-12 gap-2 p-3 bg-white rounded-xl border"
                [class.border-red-300]="!isDraftValid(d)" [class.border-gray-200]="isDraftValid(d)">
                <input [(ngModel)]="d.title" [name]="'dt' + i" maxlength="150" placeholder="Titre" aria-label="Titre"
                    class="md:col-span-3 px-3 py-2 rounded-lg border border-gray-300 text-sm font-bold">
                <textarea [(ngModel)]="d.description" [name]="'dd' + i" rows="1" maxlength="2000" placeholder="Description" aria-label="Description"
                    class="md:col-span-5 px-3 py-2 rounded-lg border border-gray-300 text-sm"></textarea>
                <select [(ngModel)]="d.type" [name]="'dty' + i" aria-label="Type" class="md:col-span-2 px-2 py-2 rounded-lg border border-gray-300 text-sm bg-white">
                    <option *ngFor="let t of types" [ngValue]="t">{{ typeLabels[t] }}</option>
                </select>
                <select [(ngModel)]="d.priority" [name]="'dp' + i" aria-label="Priorité" class="md:col-span-1 px-2 py-2 rounded-lg border border-gray-300 text-sm bg-white">
                    <option *ngFor="let p of priorities" [ngValue]="p">{{ p }}</option>
                </select>
                <button type="button" (click)="drafts.splice(i, 1)" class="md:col-span-1 px-2 py-2 text-sm font-bold rounded-lg bg-red-50 text-red-600 hover:bg-red-100">Retirer</button>
            </div>
        </div>

        <div class="flex flex-wrap items-center justify-end gap-3 mt-4">
            <label *ngIf="requirements.length > 0" class="mr-auto flex items-center gap-2 text-sm text-gray-700">
                <input type="checkbox" [(ngModel)]="replaceExisting" name="replaceExisting" class="rounded">
                Remplacer les {{ requirements.length }} exigence(s) déjà enregistrée(s)
            </label>
            <button type="button" (click)="drafts = []" class="px-4 py-2 rounded-lg font-bold text-gray-600 bg-gray-200 hover:bg-gray-300">Abandonner</button>
            <button type="button" (click)="saveDrafts()" [disabled]="isBusy"
                class="px-4 py-2 rounded-lg font-bold text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50">
                {{ isSaving ? 'Enregistrement...' : 'Enregistrer les exigences' }}
            </button>
        </div>
    </section>

    <!-- Exigences enregistrées -->
    <section>
        <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
            <h3 class="text-lg font-black text-gray-800">Exigences enregistrées ({{ requirements.length }})</h3>
            <div class="flex flex-wrap gap-2">
                <button *ngIf="project" type="button" (click)="openNewForm()" class="px-3 py-1.5 text-sm font-bold rounded-lg bg-indigo-100 text-indigo-700 hover:bg-indigo-200">+ Ajouter une exigence</button>
                <button *ngIf="requirements.length > 0" type="button" (click)="goTo.emit('analysis')"
                    class="px-3 py-1.5 text-sm font-bold rounded-lg text-white bg-indigo-600 hover:bg-indigo-500">Étape suivante : traçabilité →</button>
            </div>
        </div>

        <p *ngIf="!project" class="text-sm text-gray-500">Créez le projet pour enregistrer des exigences.</p>
        <p *ngIf="project && requirements.length === 0" class="text-sm text-gray-500">Aucune exigence : extrayez-les avec l'IA ou ajoutez-les manuellement.</p>

        <form *ngIf="editForm" (ngSubmit)="saveEdit()" class="p-4 mb-4 bg-gray-50 rounded-2xl border border-gray-200 grid grid-cols-1 md:grid-cols-12 gap-2">
            <input *ngIf="editingId !== null" [(ngModel)]="editForm.reference" name="ref" placeholder="REQ-001" aria-label="Référence" pattern="REQ-[0-9]{3,}"
                class="md:col-span-2 px-3 py-2 rounded-lg border border-gray-300 text-sm font-mono">
            <input [(ngModel)]="editForm.title" name="title" maxlength="150" placeholder="Titre" aria-label="Titre"
                [ngClass]="editingId !== null ? 'md:col-span-3' : 'md:col-span-4'" class="px-3 py-2 rounded-lg border border-gray-300 text-sm font-bold">
            <textarea [(ngModel)]="editForm.description" name="desc" rows="2" maxlength="2000" placeholder="Description" aria-label="Description"
                [ngClass]="editingId !== null ? 'md:col-span-4' : 'md:col-span-5'" class="px-3 py-2 rounded-lg border border-gray-300 text-sm"></textarea>
            <select [(ngModel)]="editForm.type" name="type" aria-label="Type" class="md:col-span-2 px-2 py-2 rounded-lg border border-gray-300 text-sm bg-white">
                <option *ngFor="let t of types" [ngValue]="t">{{ typeLabels[t] }}</option>
            </select>
            <select [(ngModel)]="editForm.priority" name="prio" aria-label="Priorité" class="md:col-span-1 px-2 py-2 rounded-lg border border-gray-300 text-sm bg-white">
                <option *ngFor="let p of priorities" [ngValue]="p">{{ p }}</option>
            </select>
            <div class="md:col-span-12 flex justify-end gap-2">
                <button type="button" (click)="editForm = null" class="px-4 py-2 rounded-lg font-bold text-gray-600 bg-gray-200 hover:bg-gray-300">Annuler</button>
                <button type="submit" [disabled]="isBusy" class="px-4 py-2 rounded-lg font-bold text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50">Enregistrer</button>
            </div>
        </form>

        <div *ngIf="requirements.length > 0" class="overflow-x-auto rounded-2xl border border-gray-200">
            <table class="min-w-full text-sm bg-white">
                <thead class="bg-gray-50 text-left text-gray-600">
                    <tr>
                        <th class="px-3 py-2">Réf.</th><th class="px-3 py-2">Exigence</th><th class="px-3 py-2">Type</th>
                        <th class="px-3 py-2">Priorité</th><th class="px-3 py-2">Couverture</th><th class="px-3 py-2 text-right">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <tr *ngFor="let r of requirements" class="border-t border-gray-100 align-top">
                        <td class="px-3 py-2 font-mono font-bold text-indigo-700 whitespace-nowrap">{{ r.reference }}</td>
                        <td class="px-3 py-2"><p class="font-bold text-gray-800">{{ r.title }}</p><p class="text-gray-500">{{ r.description }}</p></td>
                        <td class="px-3 py-2 whitespace-nowrap">{{ typeLabels[r.type] }}</td>
                        <td class="px-3 py-2">{{ r.priority }}</td>
                        <td class="px-3 py-2"><span class="px-2 py-0.5 rounded-full text-xs font-bold whitespace-nowrap" [ngClass]="statusClasses[r.coverage_status]">{{ statusLabels[r.coverage_status] }}</span></td>
                        <td class="px-3 py-2 text-right whitespace-nowrap">
                            <ng-container *ngIf="confirmDeleteId !== r.id">
                                <button type="button" (click)="openEditForm(r)" class="px-2 py-1 text-xs font-bold rounded-lg bg-indigo-100 text-indigo-700 hover:bg-indigo-200">Modifier</button>
                                <button type="button" (click)="confirmDeleteId = r.id" class="ml-1 px-2 py-1 text-xs font-bold rounded-lg bg-red-50 text-red-600 hover:bg-red-100">Supprimer</button>
                            </ng-container>
                            <ng-container *ngIf="confirmDeleteId === r.id">
                                <button type="button" (click)="deleteRequirement(r.id)" class="px-2 py-1 text-xs font-bold rounded-lg bg-red-600 text-white hover:bg-red-500">Confirmer</button>
                                <button type="button" (click)="confirmDeleteId = null" class="ml-1 px-2 py-1 text-xs font-bold rounded-lg bg-gray-200 text-gray-600">Annuler</button>
                            </ng-container>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </section>
  `
})
export class TrRequirementsComponent implements OnChanges {
  private service = inject(TraceabilityService);

  @Input() projectId: number | null = null;
  @Output() projectSaved = new EventEmitter<Project>();
  @Output() goTo = new EventEmitter<TrView>();

  readonly types: RequirementType[] = ['fonctionnelle', 'non_fonctionnelle'];
  readonly priorities: Priority[] = ['haute', 'moyenne', 'basse'];
  readonly typeLabels = TYPE_LABELS;
  readonly statusLabels = STATUS_LABELS;
  readonly statusClasses = STATUS_CLASSES;
  readonly maxSpecChars = MAX_SPEC_CHARS;

  project: Project | null = null;
  projectForm = { name: '', description: '' };
  specText = '';
  drafts: RequirementDraft[] = [];
  draftSource = '';
  replaceExisting = false;
  requirements: Requirement[] = [];

  editingId: number | null = null;
  editForm: (RequirementDraft & { reference: string }) | null = null;
  confirmDeleteId: number | null = null;

  isExtracting = false;
  isSaving = false;
  errorMessage = '';
  successMessage = '';

  get isBusy() {
    return this.isExtracting || this.isSaving;
  }

  ngOnChanges() {
    // Le projet vient d'être créé ici : on garde les brouillons et la saisie en cours
    if (this.project && this.project.id === this.projectId) return;
    this.project = null;
    this.requirements = [];
    this.editForm = null;
    if (this.projectId === null) {
      this.projectForm = { name: '', description: '' };
      this.specText = '';
      return;
    }
    this.service.getProject(this.projectId).subscribe({
      next: project => {
        this.applyProject(project);
        this.loadRequirements();
      },
      error: (err: Error) => this.errorMessage = err.message
    });
  }

  private applyProject(project: Project) {
    this.project = project;
    this.projectForm = { name: project.name, description: project.description ?? '' };
    this.specText = project.specification_text ?? '';
  }

  loadRequirements() {
    if (!this.project) return;
    this.service.getRequirements(this.project.id).subscribe({
      next: reqs => this.requirements = reqs,
      error: (err: Error) => this.errorMessage = err.message
    });
  }

  importSpecification(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) return;
    this.clearMessages();
    if (!/\.(txt|md|markdown)$/i.test(file.name)) {
      this.errorMessage = 'Format non supporté : importez un fichier .txt ou .md.';
      return;
    }
    if (file.size === 0 || file.size > MAX_FILE_SIZE) {
      this.errorMessage = file.size === 0 ? 'Le fichier est vide.' : 'Le fichier dépasse la taille maximale de 1 Mo.';
      return;
    }
    this.service.readTextFile(file).subscribe({
      next: result => {
        if (result.text.length > MAX_SPEC_CHARS) {
          this.errorMessage = `Le cahier des charges dépasse ${MAX_SPEC_CHARS} caractères : découpez-le.`;
          return;
        }
        this.specText = result.text;
        this.successMessage = `Fichier « ${result.filename} » importé (${result.characters} caractères).`;
      },
      error: (err: Error) => this.errorMessage = err.message
    });
  }

  extract() {
    this.clearMessages();
    this.isExtracting = true;
    this.service.extractRequirements(this.specText.trim()).subscribe({
      next: result => {
        this.drafts = result.requirements.map(r => ({ ...r }));
        this.draftSource = `Gemini (${result.model})`;
        this.isExtracting = false;
      },
      // Le texte saisi est conservé : l'utilisateur peut réessayer ou saisir les exigences à la main
      error: (err: Error) => { this.errorMessage = err.message; this.isExtracting = false; }
    });
  }

  addDraft() {
    this.drafts.push({ title: '', description: '', type: 'fonctionnelle', priority: 'moyenne' });
    if (!this.draftSource) this.draftSource = 'saisie manuelle';
  }

  isDraftValid(d: RequirementDraft): boolean {
    return d.title.trim().length >= 3 && d.title.length <= 150 && d.description.trim().length >= 3;
  }

  saveProject() {
    this.clearMessages();
    this.persistProject().subscribe({
      next: project => { this.isSaving = false; this.successMessage = `Projet « ${project.name} » enregistré.`; },
      error: (err: Error) => { this.isSaving = false; this.errorMessage = err.message; }
    });
  }

  /** Crée ou met à jour le projet avec le cahier des charges saisi. */
  private persistProject(): Observable<Project> {
    const name = this.projectForm.name.trim();
    if (name.length < 3) {
      return throwError(() => new Error('Le nom du projet doit contenir au moins 3 caractères.'));
    }
    this.isSaving = true;
    const payload = { name, description: this.projectForm.description.trim() || null, specification_text: this.specText.trim() || null };
    const request = this.project ? this.service.updateProject(this.project.id, payload) : this.service.createProject(payload);
    return request.pipe(tap(project => {
      this.project = project;
      this.projectSaved.emit(project);
    }));
  }

  saveDrafts() {
    this.clearMessages();
    if (this.drafts.some(d => !this.isDraftValid(d))) {
      this.errorMessage = 'Chaque exigence doit avoir un titre et une description d\'au moins 3 caractères (lignes en rouge).';
      return;
    }
    const drafts = this.drafts.map(d => ({ ...d, title: d.title.trim(), description: d.description.trim() }));
    this.persistProject().pipe(
      switchMap(project => this.service.saveRequirements(project.id, drafts, this.replaceExisting))
    ).subscribe({
      next: reqs => {
        this.requirements = reqs;
        this.successMessage = `${drafts.length} exigence(s) enregistrée(s).`;
        this.drafts = [];
        this.replaceExisting = false;
        this.isSaving = false;
        if (this.project) this.projectSaved.emit({ ...this.project, requirements_count: reqs.length });
      },
      error: (err: Error) => { this.errorMessage = err.message; this.isSaving = false; }
    });
  }

  openNewForm() {
    this.editingId = null;
    this.editForm = { reference: '', title: '', description: '', type: 'fonctionnelle', priority: 'moyenne' };
  }

  openEditForm(r: Requirement) {
    this.editingId = r.id;
    this.editForm = { reference: r.reference, title: r.title, description: r.description, type: r.type, priority: r.priority };
  }

  saveEdit() {
    if (!this.editForm || !this.project) return;
    this.clearMessages();
    if (!this.isDraftValid(this.editForm)) {
      this.errorMessage = 'Le titre et la description doivent contenir au moins 3 caractères.';
      return;
    }
    const { reference, ...draft } = this.editForm;
    const request = this.editingId === null
      ? this.service.createRequirement(this.project.id, draft)
      : this.service.updateRequirement(this.editingId, { ...draft, reference: reference.trim() });
    this.isSaving = true;
    request.subscribe({
      next: saved => {
        this.isSaving = false;
        this.editForm = null;
        this.successMessage = `Exigence ${saved.reference} enregistrée.`;
        this.loadRequirements();
        if (this.project) this.projectSaved.emit(this.project);
      },
      error: (err: Error) => { this.isSaving = false; this.errorMessage = err.message; }
    });
  }

  deleteRequirement(id: number) {
    this.clearMessages();
    this.service.deleteRequirement(id).subscribe({
      next: () => {
        this.confirmDeleteId = null;
        this.successMessage = 'Exigence supprimée (ses associations de traçabilité aussi).';
        this.loadRequirements();
        if (this.project) this.projectSaved.emit(this.project);
      },
      error: (err: Error) => this.errorMessage = err.message
    });
  }

  private clearMessages() {
    this.errorMessage = '';
    this.successMessage = '';
  }
}
