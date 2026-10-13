import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

export interface Prompt {
  id: number;
  name: string;
  description: string | null;
  content: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface PromptPayload {
  name: string;
  description: string | null;
  content: string;
}

export interface PromptAnalysis {
  score: number;
  verdict: string;
  strengths: string[];
  suggestions: string[];
  source: 'ia' | 'local';
  fallback_reason: string | null;
}

@Injectable({
  providedIn: 'root'
})
export class PromptService {
  private readonly apiUrl = 'http://localhost:8000/api/prompts';

  constructor(private http: HttpClient) {}

  getAll(): Observable<Prompt[]> {
    return this.http.get<Prompt[]>(this.apiUrl).pipe(catchError(this.handleError));
  }

  create(payload: PromptPayload): Observable<Prompt> {
    return this.http.post<Prompt>(this.apiUrl, payload).pipe(catchError(this.handleError));
  }

  update(id: number, payload: PromptPayload): Observable<Prompt> {
    return this.http.put<Prompt>(`${this.apiUrl}/${id}`, payload).pipe(catchError(this.handleError));
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`).pipe(catchError(this.handleError));
  }

  setDefault(id: number): Observable<Prompt> {
    return this.http.put<Prompt>(`${this.apiUrl}/${id}/default`, {}).pipe(catchError(this.handleError));
  }

  analyze(content: string): Observable<PromptAnalysis> {
    return this.http.post<PromptAnalysis>(`${this.apiUrl}/analyze`, { content }).pipe(catchError(this.handleError));
  }

  private handleError(error: HttpErrorResponse) {
    let errorMessage: string;

    if (error.status === 0) {
      errorMessage = 'Le serveur est injoignable. Vérifiez que le backend est démarré.';
    } else if (error.status === 422) {
      errorMessage = 'Données invalides : le nom doit faire 3 à 100 caractères et le contenu au moins 20 caractères.';
    } else if (typeof error.error?.detail === 'string') {
      // 400, 404, 409: the backend already sends a readable French message
      errorMessage = error.error.detail;
    } else {
      errorMessage = `Erreur serveur (${error.status}).`;
    }

    console.error('PromptService Error:', errorMessage);
    return throwError(() => new Error(errorMessage));
  }
}
