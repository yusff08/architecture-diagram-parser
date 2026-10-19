import { Injectable } from '@angular/core';
import { DiagramDocumentationResponse } from './diagram.service';

export interface GeneratedDocumentation {
  system_title: string;
  detected_actors: string[];
  documentation_markdown: string;
  prompt_name: string;
  generated_at: string;
}

const STORAGE_KEY = 'uml-analyzer.generated-docs';
const MAX_ENTRIES = 10;

/**
 * Mémorise les dernières documentations UML générées par l'analyseur,
 * pour les réutiliser dans « Exigences & Traçabilité » sans relancer l'OCR.
 */
@Injectable({
  providedIn: 'root'
})
export class GeneratedDocumentationStore {
  list(): GeneratedDocumentation[] {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]');
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  remember(result: DiagramDocumentationResponse) {
    // The backend returns "Erreur Génération" with an error message instead of a real documentation
    if (!result.documentation_markdown?.trim() || result.system_title === 'Erreur Génération') return;
    const entry: GeneratedDocumentation = {
      system_title: result.system_title,
      detected_actors: result.detected_actors ?? [],
      documentation_markdown: result.documentation_markdown,
      prompt_name: result.prompt_name,
      generated_at: new Date().toISOString()
    };
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify([entry, ...this.list()].slice(0, MAX_ENTRIES)));
    } catch {
      // Stockage indisponible (navigation privée, quota) : la fonctionnalité reste utilisable via l'import Markdown
    }
  }
}
