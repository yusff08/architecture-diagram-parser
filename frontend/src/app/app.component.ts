import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DiagramUploaderComponent } from './components/diagram-uploader/diagram-uploader.component';
import { PromptManagerComponent } from './components/prompt-manager/prompt-manager.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, DiagramUploaderComponent, PromptManagerComponent],
  template: `
    <main class="min-h-screen bg-gray-50 flex flex-col items-center py-12 px-4 sm:px-6 lg:px-8">
      <nav class="inline-flex p-1 bg-white rounded-2xl shadow-sm border border-gray-200">
        <button (click)="activeTab = 'analyzer'"
          class="px-5 py-2 rounded-xl text-sm font-bold transition-all"
          [ngClass]="activeTab === 'analyzer' ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow' : 'text-gray-600 hover:text-indigo-600'">
          Analyser un diagramme
        </button>
        <button (click)="activeTab = 'prompts'"
          class="px-5 py-2 rounded-xl text-sm font-bold transition-all"
          [ngClass]="activeTab === 'prompts' ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow' : 'text-gray-600 hover:text-indigo-600'">
          Gestion des Prompts
        </button>
      </nav>

      <app-diagram-uploader *ngIf="activeTab === 'analyzer'" class="w-full"></app-diagram-uploader>
      <app-prompt-manager *ngIf="activeTab === 'prompts'" class="w-full"></app-prompt-manager>
    </main>
  `
})
export class AppComponent {
  title = 'frontend';
  activeTab: 'analyzer' | 'prompts' = 'analyzer';
}
