import { Injectable } from '@angular/core';
import { HttpClient, HttpParams, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

export interface FaultInjectionCatalogItem {
  id: string;
  category: 'A' | 'B' | 'C' | 'D';
  category_name: string;
  name: string;
  description: string;
  parameters: Record<string, any>;
  expected_behavior: string;
}

export interface TestCase {
  id: number;
  analysis_name: string;
  use_case: string;
  actor: string | null;
  title: string;
  test_type: 'nominal' | 'limite' | 'erreur';
  injection_id: string | null;
  preconditions: string | null;
  steps: string[];
  expected_result: string;
  expected_behavior: 'erreur_4xx_message_clair' | 'mode_secours' | 'traitement_normal' | 'rejet_propre';
  priority: 'haute' | 'moyenne' | 'basse';
  status: 'a_faire' | 'passe' | 'echoue';
  generated_by_llm: boolean;
  created_at: string;
  updated_at: string;
  last_run?: TestRun | null;
}

export interface TestRun {
  id: number;
  test_case_id: number;
  started_at: string;
  duration_ms: number;
  status: 'passe' | 'echoue' | 'erreur';
  actual_behavior: string;
  details: Record<string, any>;
  injection_id: string | null;
}

export interface CategoryRobustnessScore {
  category: string;
  category_name: string;
  total_tests: number;
  passed_tests: number;
  score_percentage: number;
}

export interface TestStats {
  total: number;
  by_status: {
    a_faire: number;
    passe: number;
    echoue: number;
  };
  by_type: {
    nominal: number;
    limite: number;
    erreur: number;
  };
  by_priority: {
    haute: number;
    moyenne: number;
    basse: number;
  };
  success_rate: number;
  category_scores: Record<string, CategoryRobustnessScore>;
  global_robustness_score: number;
}

export interface GenerateTestsResponse {
  test_cases: TestCase[];
  fallback_used: boolean;
  total_generated: number;
  message: string;
}

export interface RunResultResponse {
  test_case_id: number;
  test_run: TestRun;
  new_status: 'a_faire' | 'passe' | 'echoue';
  passed: boolean;
}

export interface RunAllSummaryResponse {
  total_executed: number;
  passed: number;
  failed: number;
  errors: number;
  results: RunResultResponse[];
  duration_total_ms: number;
}

@Injectable({
  providedIn: 'root'
})
export class TestService {
  private readonly baseUrl = 'http://localhost:8000/api/tests';

  constructor(private http: HttpClient) {}

  getInjections(): Observable<FaultInjectionCatalogItem[]> {
    return this.http.get<FaultInjectionCatalogItem[]>(`${this.baseUrl}/injections`)
      .pipe(catchError(this.handleError));
  }

  getTestCases(filters?: {
    use_case?: string;
    test_type?: string;
    status?: string;
    priority?: string;
    injection_id?: string;
  }): Observable<TestCase[]> {
    let params = new HttpParams();
    if (filters) {
      if (filters.use_case) params = params.set('use_case', filters.use_case);
      if (filters.test_type) params = params.set('test_type', filters.test_type);
      if (filters.status) params = params.set('status', filters.status);
      if (filters.priority) params = params.set('priority', filters.priority);
      if (filters.injection_id) params = params.set('injection_id', filters.injection_id);
    }
    return this.http.get<TestCase[]>(this.baseUrl, { params })
      .pipe(catchError(this.handleError));
  }

  getTestCase(id: number): Observable<TestCase> {
    return this.http.get<TestCase>(`${this.baseUrl}/${id}`)
      .pipe(catchError(this.handleError));
  }

  createTestCase(testCase: Partial<TestCase>): Observable<TestCase> {
    return this.http.post<TestCase>(this.baseUrl, testCase)
      .pipe(catchError(this.handleError));
  }

  updateTestCase(id: number, testCase: Partial<TestCase>): Observable<TestCase> {
    return this.http.put<TestCase>(`${this.baseUrl}/${id}`, testCase)
      .pipe(catchError(this.handleError));
  }

  deleteTestCase(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${id}`)
      .pipe(catchError(this.handleError));
  }

  updateTestStatus(id: number, status: 'a_faire' | 'passe' | 'echoue'): Observable<TestCase> {
    return this.http.patch<TestCase>(`${this.baseUrl}/${id}/status`, { status })
      .pipe(catchError(this.handleError));
  }

  generateTests(documentation_text: string, analysis_name: string = 'Système UML', save: boolean = true): Observable<GenerateTestsResponse> {
    return this.http.post<GenerateTestsResponse>(`${this.baseUrl}/generate`, {
      documentation_text,
      analysis_name,
      save
    }).pipe(catchError(this.handleError));
  }

  runSingleTest(id: number): Observable<RunResultResponse> {
    return this.http.post<RunResultResponse>(`${this.baseUrl}/${id}/run`, {})
      .pipe(catchError(this.handleError));
  }

  runAllTests(test_ids?: number[]): Observable<RunAllSummaryResponse> {
    return this.http.post<RunAllSummaryResponse>(`${this.baseUrl}/run-all`, { test_ids })
      .pipe(catchError(this.handleError));
  }

  getTestRuns(id: number): Observable<TestRun[]> {
    return this.http.get<TestRun[]>(`${this.baseUrl}/${id}/runs`)
      .pipe(catchError(this.handleError));
  }

  getStats(): Observable<TestStats> {
    return this.http.get<TestStats>(`${this.baseUrl}/stats`)
      .pipe(catchError(this.handleError));
  }

  exportTests(format: 'markdown' | 'gherkin'): Observable<Blob> {
    return this.http.get(`${this.baseUrl}/export`, {
      params: new HttpParams().set('format', format),
      responseType: 'blob'
    }).pipe(catchError(this.handleError));
  }

  private handleError(error: HttpErrorResponse) {
    let message = 'Une erreur est survenue lors de la communication avec le serveur.';
    if (error.status === 403) {
      message = "L'injection d'anomalies est désactivée sur le serveur. Définissez ENABLE_FAULT_INJECTION=true dans le fichier .env pour activer les tests.";
    } else if (error.status === 404) {
      message = 'La ressource demandée est introuvable.';
    } else if (error.error?.detail) {
      message = typeof error.error.detail === 'string' ? error.error.detail : JSON.stringify(error.error.detail);
    } else if (error.message) {
      message = error.message;
    }
    return throwError(() => new Error(message));
  }
}
