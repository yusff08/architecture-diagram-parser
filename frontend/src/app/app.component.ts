import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DiagramUploaderComponent } from './components/diagram-uploader/diagram-uploader.component';
import { TestManagerComponent } from './components/test-manager/test-manager.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, DiagramUploaderComponent, TestManagerComponent],
  template: `
    <div class="min-h-screen bg-slate-50 flex flex-col font-sans">
      
      <!-- Barre de navigation supérieure -->
      <header class="bg-white/80 backdrop-blur-md border-b border-slate-200 sticky top-0 z-40">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          
          <!-- Logo & Titre de l'application -->
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-indigo-200">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
            <div>
              <span class="text-base font-extrabold text-slate-800 tracking-tight">UML Architecture Analyzer</span>
              <span class="hidden sm:inline-block ml-2 px-2 py-0.5 text-[10px] font-bold bg-indigo-50 text-indigo-700 rounded-full border border-indigo-100">v1.2-robustness</span>
            </div>
          </div>

          <!-- Onglets de navigation -->
          <nav class="flex items-center gap-1.5 p-1 bg-slate-100/80 rounded-2xl border border-slate-200/60">
            
            <button 
              (click)="currentTab = 'diagram'"
              [class]="currentTab === 'diagram' ? 'bg-white text-indigo-600 shadow-sm font-bold' : 'text-slate-600 hover:text-slate-900 font-semibold'"
              class="flex items-center gap-2 px-4 py-2 rounded-xl text-xs transition-all">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <span>Analyse UML</span>
            </button>

            <button 
              (click)="currentTab = 'tests'"
              [class]="currentTab === 'tests' ? 'bg-white text-indigo-600 shadow-sm font-bold' : 'text-slate-600 hover:text-slate-900 font-semibold'"
              class="flex items-center gap-2 px-4 py-2 rounded-xl text-xs transition-all">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Gestion des Tests</span>
              <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
            </button>

          </nav>

        </div>
      </header>

      <!-- Contenu principal -->
      <main class="flex-1 py-6">
        <ng-container *ngIf="currentTab === 'diagram'">
          <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col items-center justify-center py-6">
            <app-diagram-uploader class="w-full"></app-diagram-uploader>
          </div>
        </ng-container>

        <ng-container *ngIf="currentTab === 'tests'">
          <app-test-manager></app-test-manager>
        </ng-container>
      </main>

      <!-- Pied de page discret -->
      <footer class="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-400">
        UML Architecture Analyzer • Module Qualité & Test de Robustesse
      </footer>

    </div>
  `
})
export class AppComponent {
  title = 'frontend';
  currentTab: 'diagram' | 'tests' = 'tests';
}
