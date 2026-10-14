import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DocumentationViewerComponent } from '../documentation-viewer/documentation-viewer.component';
import { UMLReviewResponse } from '../../services/uml-review.service';

@Component({
  selector: 'app-uml-review-viewer',
  standalone: true,
  imports: [CommonModule, DocumentationViewerComponent],
  templateUrl: './uml-review-viewer.component.html'
})
export class UmlReviewViewerComponent {
  @Input({ required: true }) review!: UMLReviewResponse;
  showImprovedDocumentation = false;

  severityClasses(severity: UMLReviewResponse['issues'][number]['severity']): string {
    switch (severity) {
      case 'CRITIQUE':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'MOYEN':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'FAIBLE':
        return 'bg-blue-100 text-blue-800 border-blue-200';
    }
  }

  scoreClasses(): string {
    if (this.review.score < 50) {
      return 'text-red-700 bg-red-50';
    }
    if (this.review.score < 75) {
      return 'text-amber-700 bg-amber-50';
    }
    return 'text-green-700 bg-green-50';
  }
}
