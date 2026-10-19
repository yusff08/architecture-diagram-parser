import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TraceabilityService, RequirementDraft } from './traceability.service';
import { GeneratedDocumentationStore } from './generated-documentation.store';

describe('TraceabilityService', () => {
  let service: TraceabilityService;
  let http: HttpTestingController;
  const api = 'http://localhost:8000/api/traceability';

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(TraceabilityService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('extrait les exigences via le backend', () => {
    let count = 0;
    service.extractRequirements('Le client doit pouvoir se connecter.').subscribe(r => count = r.requirements.length);
    const req = http.expectOne(`${api}/requirements/extract`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ text: 'Le client doit pouvoir se connecter.' });
    req.flush({ requirements: [{ title: 'Connexion', description: 'Se connecter', type: 'fonctionnelle', priority: 'haute' }], source: 'ia', model: 'm' });
    expect(count).toBe(1);
  });

  it('enregistre les exigences validées en une seule requête', () => {
    const drafts: RequirementDraft[] = [{ title: 'Connexion', description: 'Se connecter', type: 'fonctionnelle', priority: 'haute' }];
    service.saveRequirements(3, drafts, true).subscribe();
    const req = http.expectOne(`${api}/projects/3/requirements/bulk`);
    expect(req.request.body).toEqual({ requirements: drafts, replace_existing: true });
    req.flush([]);
  });

  it('transmet le document pour la matrice et l\'export CSV', () => {
    service.getMatrix(1, 7).subscribe();
    http.expectOne(`${api}/projects/1/matrix?document_id=7`).flush({});
    service.downloadMatrixCsv(1).subscribe();
    const csv = http.expectOne(`${api}/projects/1/matrix.csv`);
    expect(csv.request.responseType).toBe('blob');
    csv.flush(new Blob(['a;b']));
  });

  it('affiche le message d\'erreur du backend (ex : quota Gemini)', () => {
    let message = '';
    service.analyze(1, 2).subscribe({ error: (e: Error) => message = e.message });
    http.expectOne(`${api}/projects/1/analyze`).flush({ detail: 'Quota Gemini dépassé' }, { status: 429, statusText: 'Too Many Requests' });
    expect(message).toBe('Quota Gemini dépassé');
  });

  it('signale un backend injoignable', () => {
    let message = '';
    service.getProjects().subscribe({ error: (e: Error) => message = e.message });
    http.expectOne(`${api}/projects`).error(new ProgressEvent('error'), { status: 0 });
    expect(message).toContain('injoignable');
  });

  it('résume les erreurs de validation 422', () => {
    let message = '';
    service.createProject({ name: 'ab' }).subscribe({ error: (e: Error) => message = e.message });
    http.expectOne(`${api}/projects`).flush(
      { detail: [{ loc: ['body', 'name'], msg: 'String should have at least 3 characters' }] },
      { status: 422, statusText: 'Unprocessable Entity' });
    expect(message).toContain('name');
  });
});

describe('GeneratedDocumentationStore', () => {
  let store: GeneratedDocumentationStore;

  beforeEach(() => {
    localStorage.removeItem('uml-analyzer.generated-docs');
    store = new GeneratedDocumentationStore();
  });

  it('mémorise les documentations générées, la plus récente en premier', () => {
    const base = { detected_actors: ['Client'], ocr_snippets: [], prompt_name: 'P' };
    store.remember({ ...base, system_title: 'A', documentation_markdown: '# A' });
    store.remember({ ...base, system_title: 'B', documentation_markdown: '# B' });
    expect(store.list().map(d => d.system_title)).toEqual(['B', 'A']);
  });

  it('ignore les résultats en erreur ou vides', () => {
    const base = { detected_actors: [], ocr_snippets: [], prompt_name: 'P' };
    store.remember({ ...base, system_title: 'Erreur Génération', documentation_markdown: 'Une erreur...' });
    store.remember({ ...base, system_title: 'Vide', documentation_markdown: '  ' });
    expect(store.list()).toEqual([]);
  });

  it('résiste à un stockage corrompu', () => {
    localStorage.setItem('uml-analyzer.generated-docs', '{pas du json');
    expect(store.list()).toEqual([]);
  });
});
