import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PromptService, Prompt, PromptPayload, PromptAnalysis } from '../../services/prompt.service';

@Component({
  selector: 'app-prompt-manager',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="max-w-3xl mx-auto mt-10 p-8 bg-white/70 backdrop-blur-xl rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.08)] border border-gray-100">

        <div class="flex items-center justify-between mb-8">
            <div>
                <h2 class="text-3xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-500">
                    Gestion des Prompts
                </h2>
                <p class="text-gray-500 mt-2 font-medium">Créez et comparez les instructions envoyées à l'IA.</p>
            </div>
            <button *ngIf="!isFormOpen" (click)="openCreateForm()"
                class="px-5 py-3 rounded-xl font-bold text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 shadow-[0_4px_14px_0_rgb(99,102,241,0.39)] active:scale-95 transition-all">
                + Nouveau prompt
            </button>
        </div>

        <div *ngIf="errorMessage" class="mb-6 p-4 border-l-4 border-red-500 bg-red-50 text-red-700 rounded-r-lg font-medium">
            {{ errorMessage }}
        </div>
        <div *ngIf="successMessage" class="mb-6 p-4 border-l-4 border-green-500 bg-green-50 text-green-700 rounded-r-lg font-medium">
            {{ successMessage }}
        </div>

        <!-- Create / Edit form -->
        <form *ngIf="isFormOpen" (ngSubmit)="save()" class="mb-8 p-6 bg-gray-50 rounded-2xl border border-gray-200 space-y-4">
            <h3 class="text-lg font-black text-gray-800">{{ editingId ? 'Modifier le prompt' : 'Nouveau prompt' }}</h3>

            <div>
                <label class="block text-sm font-bold text-gray-700 mb-1">Nom *</label>
                <input [(ngModel)]="form.name" name="name" required minlength="3" maxlength="100"
                    placeholder="Ex : Résumé court"
                    class="w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500">
            </div>

            <div>
                <label class="block text-sm font-bold text-gray-700 mb-1">Description</label>
                <input [(ngModel)]="form.description" name="description" maxlength="255"
                    placeholder="À quoi sert ce prompt ?"
                    class="w-full px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500">
            </div>

            <div>
                <label class="block text-sm font-bold text-gray-700 mb-1">Contenu du prompt * <span class="font-normal text-gray-400">(min. 20 caractères)</span></label>
                <textarea [(ngModel)]="form.content" name="content" required minlength="20" rows="8"
                    placeholder="Tu es un ... Ton rôle est de ..."
                    class="w-full px-4 py-2 rounded-lg border border-gray-300 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"></textarea>
                <p class="mt-1 text-xs text-gray-400">Le format de réponse JSON est ajouté automatiquement par le serveur, inutile de l'écrire.</p>
            </div>

            <!-- Quality analysis (AI + local fallback) -->
            <div *ngIf="analysis" class="p-4 bg-white rounded-xl border border-gray-200 space-y-3">
                <div class="flex items-center justify-between">
                    <span class="text-sm font-bold text-gray-700">Qualité : {{ analysis.score }}/100 · {{ analysis.verdict }}</span>
                    <span class="px-2 py-0.5 rounded-full text-xs font-bold"
                        [ngClass]="analysis.source === 'ia' ? 'bg-indigo-100 text-indigo-800' : 'bg-amber-100 text-amber-800'">
                        {{ analysis.source === 'ia' ? 'Analyse IA (Gemini)' : 'Analyse locale (fallback)' }}
                    </span>
                </div>
                <div class="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div class="h-full rounded-full transition-all duration-500" [style.width.%]="analysis.score"
                        [ngClass]="analysis.score >= 80 ? 'bg-green-500' : analysis.score >= 50 ? 'bg-amber-500' : 'bg-red-500'"></div>
                </div>
                <p *ngIf="analysis.fallback_reason" class="text-xs text-amber-700">IA indisponible : {{ analysis.fallback_reason }}</p>
                <ul *ngIf="analysis.strengths.length" class="text-sm text-green-700 space-y-1">
                    <li *ngFor="let s of analysis.strengths">✓ {{ s }}</li>
                </ul>
                <ul *ngIf="analysis.suggestions.length" class="text-sm text-gray-700 space-y-1">
                    <li *ngFor="let s of analysis.suggestions">→ {{ s }}</li>
                </ul>
            </div>

            <div class="flex justify-end space-x-3">
                <button type="button" (click)="analyzeQuality()" [disabled]="isAnalyzing"
                    class="mr-auto px-4 py-2 rounded-lg font-bold text-indigo-700 bg-indigo-100 hover:bg-indigo-200 disabled:opacity-50">
                    {{ isAnalyzing ? 'Analyse en cours...' : 'Analyser la qualité' }}
                </button>
                <button type="button" (click)="closeForm()" class="px-4 py-2 rounded-lg font-bold text-gray-600 bg-gray-200 hover:bg-gray-300">
                    Annuler
                </button>
                <button type="submit" [disabled]="isSaving" class="px-4 py-2 rounded-lg font-bold text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50">
                    {{ isSaving ? 'Enregistrement...' : 'Enregistrer' }}
                </button>
            </div>
        </form>

        <!-- List -->
        <p *ngIf="isLoading" class="text-center text-gray-500">Chargement...</p>
        <p *ngIf="!isLoading && prompts.length === 0 && !errorMessage" class="text-center text-gray-500">Aucun prompt pour le moment.</p>

        <div class="space-y-4">
            <div *ngFor="let prompt of prompts" class="p-5 bg-white rounded-2xl border shadow-sm"
                [class.border-indigo-300]="prompt.is_default" [class.border-gray-200]="!prompt.is_default">

                <div class="flex items-start justify-between">
                    <div class="min-w-0">
                        <div class="flex items-center space-x-2">
                            <h4 class="text-lg font-bold text-gray-800 truncate">{{ prompt.name }}</h4>
                            <span *ngIf="prompt.is_default" class="px-2 py-0.5 rounded-full text-xs font-bold bg-indigo-100 text-indigo-800">Par défaut</span>
                        </div>
                        <p *ngIf="prompt.description" class="text-sm text-gray-500 mt-1">{{ prompt.description }}</p>
                    </div>
                </div>

                <pre class="mt-3 p-3 bg-gray-50 rounded-lg text-xs text-gray-600 whitespace-pre-wrap font-mono"
                    [class.max-h-24]="expandedId !== prompt.id" [class.overflow-hidden]="expandedId !== prompt.id">{{ prompt.content }}</pre>
                <button (click)="toggleExpand(prompt.id)" class="mt-1 text-xs font-bold text-indigo-600 hover:underline">
                    {{ expandedId === prompt.id ? 'Réduire' : 'Voir tout' }}
                </button>

                <div *ngIf="confirmDeleteId !== prompt.id" class="flex flex-wrap gap-2 mt-4">
                    <button (click)="openEditForm(prompt)" class="px-3 py-1.5 text-sm font-bold rounded-lg bg-indigo-100 text-indigo-700 hover:bg-indigo-200">Modifier</button>
                    <button *ngIf="!prompt.is_default" (click)="setDefault(prompt)" class="px-3 py-1.5 text-sm font-bold rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200">Définir par défaut</button>
                    <button *ngIf="!prompt.is_default" (click)="confirmDeleteId = prompt.id" class="px-3 py-1.5 text-sm font-bold rounded-lg bg-red-50 text-red-600 hover:bg-red-100">Supprimer</button>
                </div>

                <div *ngIf="confirmDeleteId === prompt.id" class="flex items-center gap-2 mt-4 p-3 bg-red-50 rounded-lg">
                    <span class="text-sm font-medium text-red-700 mr-auto">Supprimer « {{ prompt.name }} » ?</span>
                    <button (click)="confirmDeleteId = null" class="px-3 py-1.5 text-sm font-bold rounded-lg bg-white text-gray-700 hover:bg-gray-100">Annuler</button>
                    <button (click)="delete(prompt)" class="px-3 py-1.5 text-sm font-bold rounded-lg bg-red-600 text-white hover:bg-red-500">Oui, supprimer</button>
                </div>
            </div>
        </div>
    </div>
  `
})
export class PromptManagerComponent implements OnInit {
  private promptService = inject(PromptService);

  prompts: Prompt[] = [];
  isLoading = false;
  isSaving = false;
  errorMessage = '';
  successMessage = '';

  isFormOpen = false;
  editingId: number | null = null;
  form: PromptPayload = { name: '', description: '', content: '' };

  analysis: PromptAnalysis | null = null;
  isAnalyzing = false;

  expandedId: number | null = null;
  confirmDeleteId: number | null = null;

  ngOnInit() {
    this.loadPrompts();
  }

  loadPrompts() {
    this.isLoading = true;
    this.promptService.getAll().subscribe({
      next: (prompts) => {
        this.prompts = prompts;
        this.isLoading = false;
      },
      error: (err: Error) => {
        this.errorMessage = err.message;
        this.isLoading = false;
      }
    });
  }

  openCreateForm() {
    this.editingId = null;
    this.form = { name: '', description: '', content: '' };
    this.isFormOpen = true;
    this.analysis = null;
    this.clearMessages();
  }

  openEditForm(prompt: Prompt) {
    this.editingId = prompt.id;
    this.form = { name: prompt.name, description: prompt.description ?? '', content: prompt.content };
    this.isFormOpen = true;
    this.analysis = null;
    this.clearMessages();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  closeForm() {
    this.isFormOpen = false;
    this.editingId = null;
    this.analysis = null;
  }

  analyzeQuality() {
    this.clearMessages();
    const content = this.form.content.trim();
    if (content.length < 20) {
      this.errorMessage = "Écrivez au moins 20 caractères avant de lancer l'analyse.";
      return;
    }

    this.isAnalyzing = true;
    this.promptService.analyze(content).subscribe({
      next: (analysis) => {
        this.analysis = analysis;
        this.isAnalyzing = false;
      },
      error: (err: Error) => {
        this.errorMessage = err.message;
        this.isAnalyzing = false;
      }
    });
  }

  save() {
    this.clearMessages();
    const payload: PromptPayload = {
      name: this.form.name.trim(),
      description: this.form.description?.trim() || null,
      content: this.form.content.trim()
    };

    if (payload.name.length < 3 || payload.content.length < 20) {
      this.errorMessage = 'Le nom doit faire au moins 3 caractères et le contenu au moins 20 caractères.';
      return;
    }

    this.isSaving = true;
    const request = this.editingId
      ? this.promptService.update(this.editingId, payload)
      : this.promptService.create(payload);

    request.subscribe({
      next: () => {
        this.successMessage = this.editingId ? 'Prompt modifié avec succès.' : 'Prompt créé avec succès.';
        this.isSaving = false;
        this.closeForm();
        this.loadPrompts();
      },
      error: (err: Error) => {
        this.errorMessage = err.message;
        this.isSaving = false;
      }
    });
  }

  delete(prompt: Prompt) {
    this.clearMessages();
    this.promptService.delete(prompt.id).subscribe({
      next: () => {
        this.successMessage = `Prompt « ${prompt.name} » supprimé.`;
        this.confirmDeleteId = null;
        this.loadPrompts();
      },
      error: (err: Error) => {
        this.errorMessage = err.message;
        this.confirmDeleteId = null;
      }
    });
  }

  setDefault(prompt: Prompt) {
    this.clearMessages();
    this.promptService.setDefault(prompt.id).subscribe({
      next: () => {
        this.successMessage = `« ${prompt.name} » est maintenant le prompt par défaut.`;
        this.loadPrompts();
      },
      error: (err: Error) => this.errorMessage = err.message
    });
  }

  toggleExpand(id: number) {
    this.expandedId = this.expandedId === id ? null : id;
  }

  private clearMessages() {
    this.errorMessage = '';
    this.successMessage = '';
  }
}
