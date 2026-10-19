import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

export type RequirementType = 'fonctionnelle' | 'non_fonctionnelle';
export type Priority = 'haute' | 'moyenne' | 'basse';
export type AnalyzedStatus = 'couverte' | 'partielle' | 'non_couverte' | 'a_verifier';
export type CoverageStatus = AnalyzedStatus | 'non_analysee';

export const STATUS_LABELS: Record<CoverageStatus, string> = {
  couverte: 'Couverte',
  partielle: 'Partiellement couverte',
  non_couverte: 'Non couverte',
  a_verifier: 'À vérifier manuellement',
  non_analysee: 'Non analysée'
};

export const STATUS_CLASSES: Record<CoverageStatus, string> = {
  couverte: 'bg-green-100 text-green-800',
  partielle: 'bg-amber-100 text-amber-800',
  non_couverte: 'bg-red-100 text-red-800',
  a_verifier: 'bg-sky-100 text-sky-800',
  non_analysee: 'bg-gray-100 text-gray-600'
};

export const TYPE_LABELS: Record<RequirementType, string> = {
  fonctionnelle: 'Fonctionnelle',
  non_fonctionnelle: 'Non fonctionnelle'
};

export interface Project {
  id: number;
  name: string;
  description: string | null;
  specification_text: string | null;
  active_document_id: number | null;
  requirements_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectPayload {
  name: string;
  description?: string | null;
  specification_text?: string | null;
}

export interface RequirementDraft {
  title: string;
  description: string;
  type: RequirementType;
  priority: Priority;
}

export interface Requirement extends RequirementDraft {
  id: number;
  project_id: number;
  reference: string;
  coverage_status: CoverageStatus;
  created_at: string;
  updated_at: string;
}

export interface ExtractionResult {
  requirements: RequirementDraft[];
  source: 'ia';
  model: string;
}

export interface TextFile {
  filename: string;
  text: string;
  characters: number;
}

export interface UmlElement {
  id: number;
  document_id: number;
  kind: 'actor' | 'use_case';
  name: string;
  actors: string[];
  origin: 'ia' | 'manuel' | 'generation';
}

export interface UmlDocumentSummary {
  id: number;
  project_id: number;
  name: string;
  source: string;
  system_title: string | null;
  actors_count: number;
  use_cases_count: number;
  created_at: string;
}

export interface UmlDocument extends UmlDocumentSummary {
  markdown: string;
  elements: UmlElement[];
}

export interface UmlDocumentPayload {
  name: string;
  source: 'generated' | 'import' | 'manual';
  system_title?: string | null;
  markdown: string;
  detected_actors?: string[];
}

export interface CoverageStats {
  total: number;
  functional: number;
  non_functional: number;
  covered: number;
  partial: number;
  uncovered: number;
  to_verify: number;
  not_analyzed: number;
  analyzable_functional: number;
  coverage_rate: number | null;
  formula: string;
}

export interface MatrixRow {
  requirement_id: number;
  reference: string;
  title: string;
  description: string;
  type: RequirementType;
  priority: Priority;
  use_cases: { id: number; name: string }[];
  status: CoverageStatus;
  justification: string | null;
  recommendation: string | null;
  origin: 'ia' | 'manuel' | null;
}

export interface Matrix {
  project_id: number;
  document_id: number | null;
  document_name: string | null;
  rows: MatrixRow[];
  stats: CoverageStats;
  use_cases: UmlElement[];
}

export interface Analysis {
  id: number;
  project_id: number;
  project_name: string | null;
  document_id: number | null;
  document_name: string | null;
  model: string;
  summary: string;
  suggestions: string[];
  stats: CoverageStats;
  created_at: string;
}

export interface AnalysisResult {
  analysis: Analysis;
  matrix: Matrix;
  ignored_use_cases: string[];
}

export interface CoveragePayload {
  document_id: number;
  status: AnalyzedStatus;
  use_case_ids: number[];
  justification: string;
  recommendation?: string | null;
}

export interface Dashboard {
  projects_count: number;
  analyses_count: number;
  totals: CoverageStats;
  projects: {
    id: number;
    name: string;
    requirements_count: number;
    active_document_id: number | null;
    stats: CoverageStats | null;
    last_analysis_at: string | null;
  }[];
  recent_analyses: Analysis[];
}

@Injectable({
  providedIn: 'root'
})
export class TraceabilityService {
  readonly apiUrl = 'http://localhost:8000/api/traceability';

  constructor(private http: HttpClient) {}

  // --- Projets ---
  getDashboard(): Observable<Dashboard> {
    return this.http.get<Dashboard>(`${this.apiUrl}/dashboard`).pipe(catchError(handleError));
  }

  getProjects(): Observable<Project[]> {
    return this.http.get<Project[]>(`${this.apiUrl}/projects`).pipe(catchError(handleError));
  }

  getProject(id: number): Observable<Project> {
    return this.http.get<Project>(`${this.apiUrl}/projects/${id}`).pipe(catchError(handleError));
  }

  createProject(payload: ProjectPayload): Observable<Project> {
    return this.http.post<Project>(`${this.apiUrl}/projects`, payload).pipe(catchError(handleError));
  }

  updateProject(id: number, payload: ProjectPayload): Observable<Project> {
    return this.http.put<Project>(`${this.apiUrl}/projects/${id}`, payload).pipe(catchError(handleError));
  }

  deleteProject(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/projects/${id}`).pipe(catchError(handleError));
  }

  // --- Exigences ---
  extractRequirements(text: string): Observable<ExtractionResult> {
    return this.http.post<ExtractionResult>(`${this.apiUrl}/requirements/extract`, { text }).pipe(catchError(handleError));
  }

  getRequirements(projectId: number): Observable<Requirement[]> {
    return this.http.get<Requirement[]>(`${this.apiUrl}/projects/${projectId}/requirements`).pipe(catchError(handleError));
  }

  createRequirement(projectId: number, draft: RequirementDraft): Observable<Requirement> {
    return this.http.post<Requirement>(`${this.apiUrl}/projects/${projectId}/requirements`, draft).pipe(catchError(handleError));
  }

  saveRequirements(projectId: number, requirements: RequirementDraft[], replaceExisting: boolean): Observable<Requirement[]> {
    return this.http.post<Requirement[]>(`${this.apiUrl}/projects/${projectId}/requirements/bulk`,
      { requirements, replace_existing: replaceExisting }).pipe(catchError(handleError));
  }

  updateRequirement(id: number, payload: RequirementDraft & { reference: string }): Observable<Requirement> {
    return this.http.put<Requirement>(`${this.apiUrl}/requirements/${id}`, payload).pipe(catchError(handleError));
  }

  deleteRequirement(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/requirements/${id}`).pipe(catchError(handleError));
  }

  readTextFile(file: File): Observable<TextFile> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<TextFile>(`${this.apiUrl}/files/read-text`, formData).pipe(catchError(handleError));
  }

  // --- Documents UML ---
  getDocuments(projectId: number): Observable<UmlDocumentSummary[]> {
    return this.http.get<UmlDocumentSummary[]>(`${this.apiUrl}/projects/${projectId}/documents`).pipe(catchError(handleError));
  }

  getDocument(id: number): Observable<UmlDocument> {
    return this.http.get<UmlDocument>(`${this.apiUrl}/documents/${id}`).pipe(catchError(handleError));
  }

  createDocument(projectId: number, payload: UmlDocumentPayload): Observable<UmlDocument> {
    return this.http.post<UmlDocument>(`${this.apiUrl}/projects/${projectId}/documents`, payload).pipe(catchError(handleError));
  }

  setActiveDocument(projectId: number, documentId: number): Observable<Project> {
    return this.http.put<Project>(`${this.apiUrl}/projects/${projectId}/documents/${documentId}/active`, {}).pipe(catchError(handleError));
  }

  deleteDocument(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/documents/${id}`).pipe(catchError(handleError));
  }

  extractElements(documentId: number): Observable<UmlDocument> {
    return this.http.post<UmlDocument>(`${this.apiUrl}/documents/${documentId}/extract-elements`, {}).pipe(catchError(handleError));
  }

  addElement(documentId: number, kind: 'actor' | 'use_case', name: string, actors: string[] = []): Observable<UmlElement> {
    return this.http.post<UmlElement>(`${this.apiUrl}/documents/${documentId}/elements`, { kind, name, actors }).pipe(catchError(handleError));
  }

  deleteElement(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/elements/${id}`).pipe(catchError(handleError));
  }

  // --- Traçabilité ---
  analyze(projectId: number, documentId: number): Observable<AnalysisResult> {
    return this.http.post<AnalysisResult>(`${this.apiUrl}/projects/${projectId}/analyze`, { document_id: documentId }).pipe(catchError(handleError));
  }

  getMatrix(projectId: number, documentId?: number | null): Observable<Matrix> {
    return this.http.get<Matrix>(`${this.apiUrl}/projects/${projectId}/matrix`, { params: docParams(documentId) }).pipe(catchError(handleError));
  }

  updateCoverage(projectId: number, requirementId: number, payload: CoveragePayload): Observable<Matrix> {
    return this.http.put<Matrix>(`${this.apiUrl}/projects/${projectId}/coverage/${requirementId}`, payload).pipe(catchError(handleError));
  }

  getAnalyses(projectId: number): Observable<Analysis[]> {
    return this.http.get<Analysis[]>(`${this.apiUrl}/projects/${projectId}/analyses`).pipe(catchError(handleError));
  }

  downloadMatrixCsv(projectId: number, documentId?: number | null): Observable<Blob> {
    return this.http.get(`${this.apiUrl}/projects/${projectId}/matrix.csv`, { params: docParams(documentId), responseType: 'blob' })
      .pipe(catchError(handleError));
  }

  downloadReportMarkdown(projectId: number, documentId?: number | null): Observable<string> {
    return this.http.get(`${this.apiUrl}/projects/${projectId}/report.md`, { params: docParams(documentId), responseType: 'text' })
      .pipe(catchError(handleError));
  }
}

function docParams(documentId?: number | null): HttpParams {
  return documentId != null ? new HttpParams().set('document_id', documentId) : new HttpParams();
}

/** Traduit une erreur HTTP en message français lisible (les détails viennent du backend). */
export function handleError(error: HttpErrorResponse) {
  let message: string;
  if (error.status === 0) {
    message = 'Le serveur est injoignable. Vérifiez que le backend est démarré.';
  } else if (typeof error.error?.detail === 'string') {
    message = error.error.detail;
  } else if (error.status === 422) {
    const first = Array.isArray(error.error?.detail) ? error.error.detail[0] : null;
    message = first ? `Données invalides (${(first.loc ?? []).slice(1).join('.')}) : ${first.msg}` : 'Données invalides.';
  } else {
    message = `Erreur serveur (${error.status}).`;
  }
  console.error('TraceabilityService Error:', message);
  return throwError(() => new Error(message));
}

/** Déclenche le téléchargement d'un contenu côté navigateur. */
export function saveFile(content: Blob | string, filename: string, type = 'text/plain;charset=utf-8') {
  const blob = content instanceof Blob ? content : new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
