import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { MatrixRow, CoverageStats } from '../../services/traceability.service';
import { filterMatrixRows } from './tr-matrix.component';
import { coverageSegments } from './tr-report.component';
import { TraceabilityComponent } from './traceability.component';

function row(reference: string, overrides: Partial<MatrixRow> = {}): MatrixRow {
  return {
    requirement_id: 1, reference, title: 'Titre ' + reference, description: 'desc', type: 'fonctionnelle', priority: 'moyenne',
    use_cases: [], status: 'non_analysee', justification: null, recommendation: null, origin: null, ...overrides
  };
}

describe('filterMatrixRows', () => {
  const rows = [
    row('REQ-002', { status: 'couverte', priority: 'basse', use_cases: [{ id: 1, name: 'Se connecter' }] }),
    row('REQ-001', { status: 'non_couverte', priority: 'haute', title: 'Paiement' }),
    row('REQ-003', { status: 'a_verifier', type: 'non_fonctionnelle', title: 'Performance' })
  ];

  it('trie par référence par défaut', () => {
    expect(filterMatrixRows(rows, '', '', '', '').map(r => r.reference)).toEqual(['REQ-001', 'REQ-002', 'REQ-003']);
  });

  it('recherche aussi dans les cas d\'utilisation', () => {
    expect(filterMatrixRows(rows, 'connecter', '', '', '').map(r => r.reference)).toEqual(['REQ-002']);
  });

  it('filtre par statut, type et priorité', () => {
    expect(filterMatrixRows(rows, '', 'non_couverte', '', '').length).toBe(1);
    expect(filterMatrixRows(rows, '', '', 'non_fonctionnelle', '')[0].reference).toBe('REQ-003');
    expect(filterMatrixRows(rows, '', '', '', 'haute')[0].title).toBe('Paiement');
  });

  it('trie par statut (non couvertes en premier)', () => {
    expect(filterMatrixRows(rows, '', '', '', '', 'status')[0].reference).toBe('REQ-001');
  });
});

describe('coverageSegments', () => {
  it('calcule les pourcentages de la répartition', () => {
    const stats: CoverageStats = {
      total: 4, functional: 3, non_functional: 1, covered: 2, partial: 1, uncovered: 0, to_verify: 1, not_analyzed: 0,
      analyzable_functional: 3, coverage_rate: 83.3, formula: ''
    };
    const segments = coverageSegments(stats);
    expect(segments.map(s => s.percent)).toEqual([50, 25, 0, 25, 0]);
  });

  it('ne divise pas par zéro', () => {
    const empty: CoverageStats = {
      total: 0, functional: 0, non_functional: 0, covered: 0, partial: 0, uncovered: 0, to_verify: 0, not_analyzed: 0,
      analyzable_functional: 0, coverage_rate: null, formula: ''
    };
    expect(coverageSegments(empty).every(s => s.percent === 0)).toBeTrue();
  });
});

describe('TraceabilityComponent', () => {
  beforeEach(() => {
    localStorage.removeItem('uml-analyzer.traceability.view');
    localStorage.removeItem('uml-analyzer.traceability.project');
    TestBed.configureTestingModule({
      imports: [TraceabilityComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()]
    });
  });

  it('affiche le tableau de bord et les projets du backend', () => {
    const fixture = TestBed.createComponent(TraceabilityComponent);
    fixture.detectChanges();
    const http = TestBed.inject(HttpTestingController);
    http.expectOne('http://localhost:8000/api/traceability/projects').flush([
      { id: 1, name: 'Réservation', description: null, specification_text: null, active_document_id: null,
        requirements_count: 5, created_at: '', updated_at: '' }
    ]);
    http.expectOne('http://localhost:8000/api/traceability/dashboard').flush({
      projects_count: 1, analyses_count: 0, recent_analyses: [],
      projects: [{ id: 1, name: 'Réservation', requirements_count: 5, active_document_id: null, stats: null, last_analysis_at: null }],
      totals: { total: 5, functional: 4, non_functional: 1, covered: 0, partial: 0, uncovered: 0, to_verify: 0, not_analyzed: 5,
        analyzable_functional: 0, coverage_rate: null, formula: '' }
    });
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Exigences & Traçabilité');
    expect(text).toContain('Réservation');
    expect(text).toContain('Nouvelle analyse');
    http.verify();
  });

  it('« Nouvelle analyse » ouvre la page des exigences sans projet', () => {
    const fixture = TestBed.createComponent(TraceabilityComponent);
    const component = fixture.componentInstance;
    component.projectId = 4;
    component.startNewAnalysis();
    expect(component.view).toBe('requirements');
    expect(component.projectId).toBeNull();
  });
});
