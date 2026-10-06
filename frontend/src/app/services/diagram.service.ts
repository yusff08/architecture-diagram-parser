import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

export interface ExtractedTextSnippet {
  text: string;
  confidence: number;
}

export interface DiagramDocumentationResponse {
  system_title: string;
  detected_actors: string[];
  documentation_markdown: string;
  ocr_snippets: ExtractedTextSnippet[];
}

@Injectable({
  providedIn: 'root'
})
export class DiagramService {
  private readonly apiUrl = 'http://localhost:8000/api/upload-diagram';

  constructor(private http: HttpClient) {}

  uploadDiagram(file: File): Observable<DiagramDocumentationResponse> {
    const formData = new FormData();
    formData.append('file', file);

    return this.http.post<DiagramDocumentationResponse>(this.apiUrl, formData).pipe(
      catchError(this.handleError)
    );
  }

  private handleError(error: HttpErrorResponse) {
    let errorMessage = 'An unknown error occurred while uploading the diagram.';

    if (error.error instanceof ErrorEvent) {
      errorMessage = `Network Error: ${error.error.message}`;
    } else {
      const serverDetail = error.error?.detail ? JSON.stringify(error.error.detail) : error.message;
      
      switch (error.status) {
        case 413:
          errorMessage = 'The uploaded file is too large (Max 10 MB).';
          break;
        case 415:
          errorMessage = 'Unsupported file type. Please upload a valid JPEG, PNG, or WebP.';
          break;
        case 500:
        case 502:
          errorMessage = `AI Processing failed on the server. Details: ${serverDetail}`;
          break;
        case 504:
        case 0:
          errorMessage = 'The server timed out or is unreachable. The image might be too complex or the backend is offline.';
          break;
        default:
          errorMessage = `Server Error (${error.status}): ${serverDetail}`;
      }
    }

    console.error('DiagramService Error:', errorMessage);
    return throwError(() => new Error(errorMessage));
  }
}
