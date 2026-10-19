import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

export type Severity = 'CRITIQUE' | 'MOYEN' | 'FAIBLE';
export type IssueClassification = 'ERREUR_CONFIRMEE' | 'AMELIORATION_POTENTIELLE';
export type MissingElementConfidence = 'faible' | 'moyenne' | 'élevée';

export interface UMLIssue {
  title: string;
  severity: Severity;
  classification: IssueClassification;
  description: string;
  reason: string;
  suggestion: string;
}

export interface PossibleMissingElement {
  element: string;
  reason: string;
  confidence: MissingElementConfidence;
}

export interface UMLReviewResponse {
  score: number;
  summary: string;
  issues: UMLIssue[];
  strengths: string[];
  possible_missing_elements: PossibleMissingElement[];
  improved_documentation_markdown: string;
}

@Injectable({
  providedIn: 'root'
})
export class UmlReviewService {
  private readonly apiUrl = 'http://localhost:8000/api/review-documentation';

  constructor(private http: HttpClient) {}

  reviewDocumentation(documentationMarkdown: string): Observable<UMLReviewResponse> {
    return this.http.post<UMLReviewResponse>(this.apiUrl, {
      documentation_markdown: documentationMarkdown
    }).pipe(
      catchError(this.handleError)
    );
  }

  private handleError(error: HttpErrorResponse) {
    let errorMessage: string;

    switch (error.status) {
      case 503:
        errorMessage = (error.error as { detail?: string })?.detail === 'gemini_temporarily_overloaded'
          ? "Le service Gemini est temporairement surchargé. Veuillez relancer l'analyse dans quelques secondes."
          : "Le service d'intelligence artificielle n'est pas configuré.";
        break;
      case 504:
        errorMessage = "L'analyse IA a dépassé le délai d'attente. Veuillez réessayer.";
        break;
      case 502:
        errorMessage = "L'IA n'a pas pu produire une analyse valide.";
        break;
      default:
        errorMessage = "Une erreur est survenue pendant l'analyse.";
    }

    return throwError(() => new Error(errorMessage));
  }
}
