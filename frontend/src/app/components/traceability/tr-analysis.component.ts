import { Component, EventEmitter, Input, OnChanges, Output, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  TraceabilityService, Project, UmlDocument, UmlDocumentSummary, Matrix, MatrixRow, Analysis, AnalyzedStatus,
  STATUS_LABELS, STATUS_CLASSES, TYPE_LABELS
} from '../../services/traceability.service';
import { GeneratedDocumentationStore, GeneratedDocumentation } from '../../services/generated-documentation.store';
import type { TrView } from './traceability.component';

@Component({
  selector: 'app-tr-analysis',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div *ngIf="errorMessage" class="mb-6 p-4 border-l-4 border-red-500 bg-red-50 text-red-700 rounded-r-lg font-medium">{{ errorMessage }}</div>
    <div *ngIf="successMessage" class="mb-6 p-4 border-l-4 border-green-500 bg-green-50 text-green-700 rounded-r-lg font-medium">{{ successMessage }}</div>

    <!-- 1. Documentation UML -->
    <section class="p-6 mb-8 bg-gray-50 rounded-2xl border border-gray-200">
        <h3 class="text-lg font-black text-gray-800 mb-1">1. Documentation UML</h3>
        <p class="text-sm text-gray-500 mb-4">Réutilisez une documentation générée par l'analyseur (sans relancer l'OCR) ou importez un fichier Markdown.</p>

        <div *ngIf="documents.length > 0" class="mb-4">
            <label for="tr-doc" class="block text-sm font-bold text-gray-700 mb-1">Document analysé</label>
            <div class="flex flex-col sm:flex-row gap-2">
                <select id="tr-doc" [ngModel]="documentId" (ngModelChange)="selectDocument($event)"
                    class="flex-1 px-4 py-2 rounded-xl border border-gray-300 bg-white font-medium text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500">
                    <option *ngFor="let d of documents" [ngValue]="d.id">{{ d.name }} — {{ d.use_cases_count }} cas d'utilisation · {{ d.actors_count }} acteur(s)</option>
                </select>
                <button *ngIf="!confirmDeleteDoc" type="button" (click)="confirmDeleteDoc = true" [disabled]="documentId === null"
                    class="px-3 py-2 text-sm font-bold rounded-xl bg-red-50 text-red-600 hover:bg-red-100">Supprimer</button>
                <ng-container *ngIf="confirmDeleteDoc">
                    <button type="button" (click)="deleteDocument()" class="px-3 py-2 text-sm font-bold rounded-xl bg-red-600 text-white hover:bg-red-500">Confirmer</button>
                    <button type="button" (click)="confirmDeleteDoc = false" class="px-3 py-2 text-sm font-bold rounded-xl bg-gray-200 text-gray-600">Annuler</button>
                </ng-container>
            </div>
        </div>
        <p *ngIf="documents.length === 0" class="mb-4 text-sm text-amber-700 font-medium">Aucune documentation UML associée à ce projet : ajoutez-en une ci-dessous.</p>

        <details class="bg-white rounded-xl border border-gray-200 p-4" [open]="documents.length === 0">
            <summary class="cursor-pointer font-bold text-indigo-700">+ Ajouter une documentation UML</summary>
            <div class="mt-4 space-y-4">
                <div>
                    <label for="tr-gen" class="block text-sm font-bold text-gray-700 mb-1">Documentation générée par l'analyseur</label>
                    <div *ngIf="generatedDocs.length > 0" class="flex flex-col sm:flex-row gap-2">
                        <select id="tr-gen" [(ngModel)]="generatedIndex" name="gen" class="flex-1 px-3 py-2 rounded-lg border border-gray-300 bg-white text-sm">
                            <option *ngFor="let g of generatedDocs; let i = index" [ngValue]="i">{{ g.system_title }} — {{ g.generated_at | date:'short' }} ({{ g.prompt_name }})</option>
                        </select>
                        <button type="button" (click)="addGeneratedDocument()" [disabled]="isBusy"
                            class="px-4 py-2 text-sm font-bold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50">Utiliser cette documentation</button>
                    </div>
                    <p *ngIf="generatedDocs.length === 0" class="text-sm text-gray-500">
                        Aucune documentation générée dans ce navigateur. Utilisez l'onglet « Analyser un diagramme » puis revenez ici.
                    </p>
                </div>

                <div class="border-t border-gray-100 pt-4">
                    <p class="block text-sm font-bold text-gray-700 mb-1">Importer ou coller un Markdown</p>
                    <div class="flex flex-col sm:flex-row gap-2 mb-2">
                        <input [(ngModel)]="newDoc.name" name="docName" maxlength="150" placeholder="Nom du document *" aria-label="Nom du document"
                            class="flex-1 px-3 py-2 rounded-lg border border-gray-300 text-sm">
                        <input #mdFile type="file" class="hidden" accept=".md,.markdown,.txt,text/markdown,text/plain" (change)="importMarkdown($event)">
                        <button type="button" (click)="mdFile.click()" [disabled]="isBusy" class="px-3 py-2 text-sm font-bold rounded-lg bg-indigo-100 text-indigo-700 hover:bg-indigo-200 disabled:opacity-50">Importer un fichier .md</button>
                    </div>
                    <textarea [(ngModel)]="newDoc.markdown" name="docMd" rows="6" placeholder="# Documentation du système..." aria-label="Markdown"
                        class="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm font-mono"></textarea>
                    <div class="flex justify-end mt-2">
                        <button type="button" (click)="addImportedDocument()" [disabled]="isBusy || newDoc.markdown.trim().length < 20 || newDoc.name.trim().length < 3"
                            class="px-4 py-2 text-sm font-bold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50">Enregistrer le document</button>
                    </div>
                </div>
            </div>
        </details>
    </section>

    <!-- 2. Acteurs et cas d'utilisation -->
    <section *ngIf="document" class="p-6 mb-8 bg-gray-50 rounded-2xl border border-gray-200">
        <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
            <div>
                <h3 class="text-lg font-black text-gray-800">2. Acteurs et cas d'utilisation</h3>
                <p class="text-sm text-gray-500">Seuls les éléments écrits explicitement dans la documentation sont conservés.</p>
            </div>
            <button type="button" (click)="extractElements()" [disabled]="isBusy"
                class="px-4 py-2 text-sm font-bold rounded-lg bg-indigo-100 text-indigo-700 hover:bg-indigo-200 disabled:opacity-50">
                {{ isExtracting ? 'Identification (Gemini)...' : 'Identifier avec Gemini' }}
            </button>
        </div>

        <div class="grid md:grid-cols-2 gap-4">
            <div *ngFor="let group of elementGroups" class="bg-white p-4 rounded-xl border border-gray-200">
                <p class="font-bold text-gray-700 mb-2">{{ group.label }} ({{ elementsOf(group.kind).length }})</p>
                <p *ngIf="elementsOf(group.kind).length === 0" class="text-sm text-gray-400">Aucun.</p>
                <ul class="flex flex-wrap gap-2 mb-3">
                    <li *ngFor="let e of elementsOf(group.kind)" class="inline-flex items-center gap-1 pl-3 pr-1 py-1 rounded-full bg-indigo-50 text-indigo-800 text-sm">
                        {{ e.name }}
                        <span class="text-[10px] uppercase text-indigo-400">{{ e.origin }}</span>
                        <button type="button" (click)="deleteElement(e.id)" class="w-5 h-5 rounded-full text-indigo-500 hover:bg-indigo-200" [attr.aria-label]="'Retirer ' + e.name">×</button>
                    </li>
                </ul>
                <div class="flex gap-2">
                    <input [(ngModel)]="newElement[group.kind]" [name]="'new-' + group.kind" maxlength="150" [placeholder]="group.placeholder" [attr.aria-label]="group.placeholder"
                        (keydown.enter)="addElement(group.kind)" class="flex-1 min-w-0 px-3 py-1.5 rounded-lg border border-gray-300 text-sm">
                    <button type="button" (click)="addElement(group.kind)" [disabled]="(newElement[group.kind] || '').trim().length < 2"
                        class="px-3 py-1.5 text-sm font-bold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50">Ajouter</button>
                </div>
            </div>
        </div>
        <details class="mt-4">
            <summary class="cursor-pointer text-sm font-bold text-gray-600">Voir la documentation Markdown</summary>
            <pre class="mt-2 p-3 bg-white rounded-lg border border-gray-200 text-xs text-gray-600 whitespace-pre-wrap max-h-72 overflow-auto">{{ document.markdown }}</pre>
        </details>
    </section>

    <!-- 3. Analyse -->
    <section *ngIf="document" class="mb-8">
        <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
            <h3 class="text-lg font-black text-gray-800">3. Correspondances exigences ↔ cas d'utilisation</h3>
            <button type="button" (click)="analyze()" [disabled]="isBusy || !matrix || matrix.rows.length === 0"
                class="flex items-center gap-2 px-5 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 shadow-[0_4px_14px_0_rgb(99,102,241,0.39)] disabled:opacity-50 disabled:shadow-none">
                <svg *ngIf="isAnalyzing" class="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
                {{ isAnalyzing ? 'Analyse en cours (Gemini)...' : 'Lancer l\\'analyse avec Gemini' }}
            </button>
        </div>

        <p *ngIf="matrix && matrix.rows.length === 0" class="p-4 text-sm text-amber-700 bg-amber-50 rounded-xl">
            Ce projet n'a aucune exigence. <button type="button" (click)="goTo.emit('requirements')" class="font-bold underline">Ajouter des exigences</button>
        </p>

        <div *ngIf="ignoredUseCases.length > 0" class="mb-4 p-3 text-sm bg-amber-50 text-amber-800 rounded-xl border border-amber-200">
            Cas d'utilisation proposés par Gemini mais absents du document (rejetés) : {{ ignoredUseCases.join(', ') }}
        </div>

        <div *ngIf="matrix && matrix.rows.length > 0" class="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4 text-center">
            <div class="p-3 bg-green-50 rounded-xl"><p class="text-2xl font-black text-green-700">{{ matrix.stats.covered }}</p><p class="text-xs font-bold text-green-800">Couvertes</p></div>
            <div class="p-3 bg-amber-50 rounded-xl"><p class="text-2xl font-black text-amber-700">{{ matrix.stats.partial }}</p><p class="text-xs font-bold text-amber-800">Partielles</p></div>
            <div class="p-3 bg-red-50 rounded-xl"><p class="text-2xl font-black text-red-700">{{ matrix.stats.uncovered }}</p><p class="text-xs font-bold text-red-800">Non couvertes</p></div>
            <div class="p-3 bg-sky-50 rounded-xl"><p class="text-2xl font-black text-sky-700">{{ matrix.stats.to_verify }}</p><p class="text-xs font-bold text-sky-800">À vérifier</p></div>
            <div class="p-3 bg-indigo-50 rounded-xl col-span-2 md:col-span-1"><p class="text-2xl font-black text-indigo-700">{{ matrix.stats.coverage_rate !== null ? matrix.stats.coverage_rate + ' %' : '—' }}</p><p class="text-xs font-bold text-indigo-800">Couverture</p></div>
        </div>

        <div class="space-y-3">
            <div *ngFor="let row of matrix?.rows" class="p-4 bg-white rounded-2xl border border-gray-200 shadow-sm">
                <div class="flex flex-col md:flex-row md:items-start gap-3">
                    <div class="flex-1 min-w-0">
                        <p class="font-bold text-gray-800"><span class="font-mono text-indigo-700">{{ row.reference }}</span> {{ row.title }}
                            <span class="ml-1 text-xs font-medium text-gray-400">{{ typeLabels[row.type] }} · {{ row.priority }}</span></p>
                        <p class="text-sm text-gray-600 mt-1">
                            <span class="font-bold">Cas d'utilisation :</span>
                            {{ row.use_cases.length ? useCaseNames(row) : (row.type === 'non_fonctionnelle' && row.status === 'a_verifier' ? 'Non vérifiable par ce diagramme' : 'Aucun') }}
                        </p>
                        <p *ngIf="row.justification" class="text-sm text-gray-500 mt-1"><span class="font-bold">Justification :</span> {{ row.justification }}</p>
                        <p *ngIf="row.recommendation" class="text-sm text-indigo-700 mt-1"><span class="font-bold">Recommandation IA :</span> {{ row.recommendation }}</p>
                    </div>
                    <div class="flex md:flex-col items-center md:items-end gap-2">
                        <span class="px-2 py-0.5 rounded-full text-xs font-bold whitespace-nowrap" [ngClass]="statusClasses[row.status]">{{ statusLabels[row.status] }}</span>
                        <span *ngIf="row.origin" class="text-[11px] text-gray-400">{{ row.origin === 'manuel' ? 'validé manuellement' : 'proposé par Gemini' }}</span>
                        <button *ngIf="editingRowId !== row.requirement_id" type="button" (click)="openEdit(row)"
                            class="px-2 py-1 text-xs font-bold rounded-lg bg-indigo-100 text-indigo-700 hover:bg-indigo-200">Corriger</button>
                    </div>
                </div>

                <form *ngIf="editingRowId === row.requirement_id" (ngSubmit)="saveEdit(row)" class="mt-3 p-4 bg-gray-50 rounded-xl border border-gray-200 space-y-3">
                    <div>
                        <label class="block text-sm font-bold text-gray-700 mb-1" [for]="'st-' + row.requirement_id">Couverture</label>
                        <select [id]="'st-' + row.requirement_id" [(ngModel)]="edit.status" name="status" class="w-full sm:w-72 px-3 py-2 rounded-lg border border-gray-300 bg-white text-sm">
                            <option *ngFor="let s of analyzedStatuses" [ngValue]="s">{{ statusLabels[s] }}</option>
                        </select>
                    </div>
                    <fieldset>
                        <legend class="text-sm font-bold text-gray-700 mb-1">Cas d'utilisation associés</legend>
                        <p *ngIf="matrix?.use_cases?.length === 0" class="text-sm text-gray-400">Aucun cas d'utilisation dans ce document.</p>
                        <div class="flex flex-wrap gap-2">
                            <label *ngFor="let uc of matrix?.use_cases" class="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-white border border-gray-200 text-sm">
                                <input type="checkbox" [checked]="edit.useCaseIds.has(uc.id)" (change)="toggleUseCase(uc.id)" [disabled]="edit.status === 'non_couverte'"> {{ uc.name }}
                            </label>
                        </div>
                    </fieldset>
                    <textarea [(ngModel)]="edit.justification" name="justification" rows="2" maxlength="2000" placeholder="Justification (obligatoire)" aria-label="Justification"
                        class="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm"></textarea>
                    <textarea [(ngModel)]="edit.recommendation" name="recommendation" rows="2" maxlength="2000" placeholder="Recommandation (facultative)" aria-label="Recommandation"
                        class="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm"></textarea>
                    <div class="flex justify-end gap-2">
                        <button type="button" (click)="editingRowId = null" class="px-4 py-2 rounded-lg font-bold text-gray-600 bg-gray-200 hover:bg-gray-300">Annuler</button>
                        <button type="submit" [disabled]="isBusy" class="px-4 py-2 rounded-lg font-bold text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50">Enregistrer la correction</button>
                    </div>
                </form>
            </div>
        </div>
    </section>

    <!-- 4. Synthèse IA -->
    <section *ngIf="lastAnalysis" class="p-6 bg-indigo-50/60 rounded-2xl border border-indigo-200">
        <h3 class="text-lg font-black text-gray-800 mb-1">Synthèse et recommandations de Gemini</h3>
        <p class="text-xs text-gray-500 mb-3">Analyse du {{ lastAnalysis.created_at }} · modèle {{ lastAnalysis.model }} · le diagramme original n'est jamais modifié.</p>
        <p class="text-sm text-gray-700 mb-3">{{ lastAnalysis.summary || 'Pas de résumé fourni.' }}</p>
        <ul class="text-sm text-gray-700 space-y-1">
            <li *ngFor="let s of lastAnalysis.suggestions">→ {{ s }}</li>
        </ul>
        <button type="button" (click)="goTo.emit('matrix')" class="mt-4 px-4 py-2 text-sm font-bold rounded-lg text-white bg-indigo-600 hover:bg-indigo-500">Voir la matrice de traçabilité →</button>
    </section>
  `
})
export class TrAnalysisComponent implements OnChanges {
  private service = inject(TraceabilityService);
  private generatedStore = inject(GeneratedDocumentationStore);

  @Input({ required: true }) projectId!: number;
  @Output() goTo = new EventEmitter<TrView>();

  readonly statusLabels = STATUS_LABELS;
  readonly statusClasses = STATUS_CLASSES;
  readonly typeLabels = TYPE_LABELS;
  readonly analyzedStatuses: AnalyzedStatus[] = ['couverte', 'partielle', 'non_couverte', 'a_verifier'];
  readonly elementGroups = [
    { kind: 'actor' as const, label: 'Acteurs', placeholder: 'Nom de l\'acteur' },
    { kind: 'use_case' as const, label: 'Cas d\'utilisation', placeholder: 'Nom du cas d\'utilisation' }
  ];

  project: Project | null = null;
  documents: UmlDocumentSummary[] = [];
  documentId: number | null = null;
  document: UmlDocument | null = null;
  matrix: Matrix | null = null;
  lastAnalysis: Analysis | null = null;
  ignoredUseCases: string[] = [];

  generatedDocs: GeneratedDocumentation[] = [];
  generatedIndex = 0;
  newDoc = { name: '', markdown: '' };
  newElement: Record<'actor' | 'use_case', string> = { actor: '', use_case: '' };
  confirmDeleteDoc = false;

  editingRowId: number | null = null;
  edit = { status: 'couverte' as AnalyzedStatus, useCaseIds: new Set<number>(), justification: '', recommendation: '' };

  isAnalyzing = false;
  isExtracting = false;
  isSaving = false;
  errorMessage = '';
  successMessage = '';

  get isBusy() {
    return this.isAnalyzing || this.isExtracting || this.isSaving;
  }

  ngOnChanges() {
    this.generatedDocs = this.generatedStore.list();
    this.document = null;
    this.matrix = null;
    this.lastAnalysis = null;
    this.service.getProject(this.projectId).subscribe({
      next: project => { this.project = project; this.loadDocuments(project.active_document_id); },
      error: (err: Error) => this.errorMessage = err.message
    });
  }

  loadDocuments(preferredId: number | null) {
    this.service.getDocuments(this.projectId).subscribe({
      next: docs => {
        this.documents = docs;
        const id = docs.some(d => d.id === preferredId) ? preferredId : docs[0]?.id ?? null;
        this.loadDocument(id);
      },
      error: (err: Error) => this.errorMessage = err.message
    });
  }

  selectDocument(id: number) {
    this.clearMessages();
    this.service.setActiveDocument(this.projectId, id).subscribe({
      next: () => this.loadDocument(id),
      error: (err: Error) => this.errorMessage = err.message
    });
  }

  private loadDocument(id: number | null) {
    this.documentId = id;
    this.ignoredUseCases = [];
    this.editingRowId = null;
    if (id === null) {
      this.document = null;
      this.matrix = null;
      return;
    }
    this.service.getDocument(id).subscribe({
      next: doc => { this.document = doc; this.refreshMatrix(); },
      error: (err: Error) => this.errorMessage = err.message
    });
    this.service.getAnalyses(this.projectId).subscribe({
      next: analyses => this.lastAnalysis = analyses.find(a => a.document_id === id) ?? null,
      error: () => this.lastAnalysis = null
    });
  }

  private refreshMatrix() {
    if (this.documentId === null) return;
    this.service.getMatrix(this.projectId, this.documentId).subscribe({
      next: matrix => this.matrix = matrix,
      error: (err: Error) => this.errorMessage = err.message
    });
  }

  addGeneratedDocument() {
    const generated = this.generatedDocs[this.generatedIndex];
    if (!generated) return;
    this.createDocument({
      name: generated.system_title || 'Documentation générée',
      source: 'generated',
      system_title: generated.system_title,
      markdown: generated.documentation_markdown,
      detected_actors: generated.detected_actors
    });
  }

  importMarkdown(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) return;
    this.clearMessages();
    if (!/\.(md|markdown|txt)$/i.test(file.name) || file.size > 1024 * 1024 || file.size === 0) {
      this.errorMessage = 'Importez un fichier .md ou .txt non vide de 1 Mo maximum.';
      return;
    }
    this.service.readTextFile(file).subscribe({
      next: result => {
        this.newDoc.markdown = result.text;
        if (!this.newDoc.name.trim()) this.newDoc.name = result.filename.replace(/\.[^.]+$/, '');
      },
      error: (err: Error) => this.errorMessage = err.message
    });
  }

  addImportedDocument() {
    this.createDocument({ name: this.newDoc.name.trim(), source: 'import', markdown: this.newDoc.markdown });
  }

  private createDocument(payload: Parameters<TraceabilityService['createDocument']>[1]) {
    this.clearMessages();
    this.isSaving = true;
    this.service.createDocument(this.projectId, payload).subscribe({
      next: doc => {
        this.isSaving = false;
        this.newDoc = { name: '', markdown: '' };
        this.successMessage = `Documentation « ${doc.name} » ajoutée au projet.`;
        this.loadDocuments(doc.id);
      },
      error: (err: Error) => { this.isSaving = false; this.errorMessage = err.message; }
    });
  }

  deleteDocument() {
    if (this.documentId === null) return;
    this.service.deleteDocument(this.documentId).subscribe({
      next: () => { this.confirmDeleteDoc = false; this.loadDocuments(null); },
      error: (err: Error) => this.errorMessage = err.message
    });
  }

  elementsOf(kind: 'actor' | 'use_case') {
    return this.document?.elements.filter(e => e.kind === kind) ?? [];
  }

  extractElements() {
    if (this.documentId === null) return;
    this.clearMessages();
    this.isExtracting = true;
    this.service.extractElements(this.documentId).subscribe({
      next: doc => {
        this.isExtracting = false;
        this.document = doc;
        this.successMessage = `${doc.use_cases_count} cas d'utilisation et ${doc.actors_count} acteur(s) identifiés.`;
        this.refreshMatrix();
        this.loadDocumentsSummaryOnly();
      },
      error: (err: Error) => { this.isExtracting = false; this.errorMessage = err.message; }
    });
  }

  addElement(kind: 'actor' | 'use_case') {
    const name = (this.newElement[kind] || '').trim();
    if (this.documentId === null || name.length < 2) return;
    this.clearMessages();
    this.service.addElement(this.documentId, kind, name).subscribe({
      next: () => { this.newElement[kind] = ''; this.reloadDocument(); },
      error: (err: Error) => this.errorMessage = err.message
    });
  }

  deleteElement(id: number) {
    this.clearMessages();
    this.service.deleteElement(id).subscribe({
      next: () => this.reloadDocument(),
      error: (err: Error) => this.errorMessage = err.message
    });
  }

  private reloadDocument() {
    if (this.documentId === null) return;
    this.service.getDocument(this.documentId).subscribe({
      next: doc => { this.document = doc; this.refreshMatrix(); this.loadDocumentsSummaryOnly(); },
      error: (err: Error) => this.errorMessage = err.message
    });
  }

  private loadDocumentsSummaryOnly() {
    this.service.getDocuments(this.projectId).subscribe({ next: docs => this.documents = docs, error: () => {} });
  }

  analyze() {
    if (this.documentId === null) return;
    this.clearMessages();
    this.isAnalyzing = true;
    this.service.analyze(this.projectId, this.documentId).subscribe({
      next: result => {
        this.isAnalyzing = false;
        this.matrix = result.matrix;
        this.lastAnalysis = result.analysis;
        this.ignoredUseCases = result.ignored_use_cases;
        this.successMessage = 'Analyse de traçabilité terminée et enregistrée.';
        this.reloadDocument();
      },
      // Les exigences et corrections déjà enregistrées restent intactes
      error: (err: Error) => { this.isAnalyzing = false; this.errorMessage = err.message; }
    });
  }

  useCaseNames(row: MatrixRow) {
    return row.use_cases.map(u => u.name).join(', ');
  }

  openEdit(row: MatrixRow) {
    this.editingRowId = row.requirement_id;
    this.edit = {
      status: row.status === 'non_analysee' ? 'couverte' : row.status,
      useCaseIds: new Set(row.use_cases.map(u => u.id)),
      justification: row.justification ?? '',
      recommendation: row.recommendation ?? ''
    };
  }

  toggleUseCase(id: number) {
    this.edit.useCaseIds.has(id) ? this.edit.useCaseIds.delete(id) : this.edit.useCaseIds.add(id);
  }

  saveEdit(row: MatrixRow) {
    if (this.documentId === null) return;
    this.clearMessages();
    const useCaseIds = this.edit.status === 'non_couverte' ? [] : [...this.edit.useCaseIds];
    if (this.edit.justification.trim().length < 3) {
      this.errorMessage = 'Indiquez une justification (au moins 3 caractères).';
      return;
    }
    if ((this.edit.status === 'couverte' || this.edit.status === 'partielle') && useCaseIds.length === 0) {
      this.errorMessage = 'Sélectionnez au moins un cas d\'utilisation pour une exigence couverte ou partiellement couverte.';
      return;
    }
    this.isSaving = true;
    this.service.updateCoverage(this.projectId, row.requirement_id, {
      document_id: this.documentId,
      status: this.edit.status,
      use_case_ids: useCaseIds,
      justification: this.edit.justification.trim(),
      recommendation: this.edit.recommendation.trim() || null
    }).subscribe({
      next: matrix => {
        this.isSaving = false;
        this.matrix = matrix;
        this.editingRowId = null;
        this.successMessage = `Correction de ${row.reference} enregistrée (elle ne sera pas écrasée par une nouvelle analyse IA).`;
      },
      error: (err: Error) => { this.isSaving = false; this.errorMessage = err.message; }
    });
  }

  private clearMessages() {
    this.errorMessage = '';
    this.successMessage = '';
  }
}
