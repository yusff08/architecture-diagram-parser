import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  TestService,
  TestCase,
  TestRun,
  TestStats,
  FaultInjectionCatalogItem,
  RunAllSummaryResponse,
  DetectAnomaliesResponse
} from '../../services/test.service';

@Component({
  selector: 'app-test-manager',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './test-manager.component.html',
  styleUrls: ['./test-manager.component.css']
})
export class TestManagerComponent implements OnInit {
  private testService = inject(TestService);

  // Données principales
  testCases: TestCase[] = [];
  injections: FaultInjectionCatalogItem[] = [];
  stats: TestStats | null = null;
  selectedTestRuns: TestRun[] = [];

  // États UI
  activeTab: 'tests' | 'generator' | 'anomalies' | 'catalog' = 'tests';
  selectedCategoryFilter: string = 'ALL';
  isLoading = false;
  isRunningAll = false;
  runAllProgress = 0;
  runningTestId: number | null = null;
  errorMessage: string | null = null;
  successMessage: string | null = null;
  warningFallbackMessage: string | null = null;

  // Filtres de recherche
  filterSearch = '';
  filterType = '';
  filterStatus = '';
  filterPriority = '';
  filterInjection = '';

  // Formulaire Générateur IA
  genDocText = `Système : Distributeur Automatique de Billets (DAB)
Acteurs : Client Porteur de Carte, Banque Centrale, Opérateur de Maintenance
Cas d'utilisation :
- S'authentifier avec carte et code PIN
- Retirer des espèces (<<include>> Vérifier Solde, <<extend>> Imprimer Ticket)
- Consulter le solde du compte
- Recharger le bac à billets`;
  genAnalysisName = 'Distributeur DAB Bancaire';
  genSaveToDb = true;

  // Détection intelligente d'anomalies (réutilise la documentation du générateur)
  anoUseAi = true;
  anoGenerateTests = false;
  isDetecting = false;
  anomalyResult: DetectAnomaliesResponse | null = null;

  // Modal Création / Édition
  showEditModal = false;
  isEditing = false;
  currentTest: Partial<TestCase> = this.getEmptyTestCase();
  newStepInput = '';

  // Modal Historique des Runs
  showRunsModal = false;
  activeTestForRuns: TestCase | null = null;

  ngOnInit(): void {
    this.loadAll();
  }

  loadAll(): void {
    this.loadStats();
    this.loadTestCases();
    this.loadInjections();
  }

  loadStats(): void {
    this.testService.getStats().subscribe({
      next: (data) => (this.stats = data),
      error: (err) => console.error('Erreur chargement statistiques:', err)
    });
  }

  loadInjections(): void {
    this.testService.getInjections().subscribe({
      next: (data) => (this.injections = data),
      error: (err) => console.error('Erreur catalogue injections:', err)
    });
  }

  loadTestCases(): void {
    this.isLoading = true;
    this.testService.getTestCases({
      use_case: this.filterSearch || undefined,
      test_type: this.filterType || undefined,
      status: this.filterStatus || undefined,
      priority: this.filterPriority || undefined,
      injection_id: this.filterInjection || undefined
    }).subscribe({
      next: (data) => {
        this.testCases = data;
        this.isLoading = false;
      },
      error: (err) => {
        this.errorMessage = err.message;
        this.isLoading = false;
      }
    });
  }

  get filteredTestCases(): TestCase[] {
    return this.testCases.filter((tc) => {
      const matchSearch =
        !this.filterSearch ||
        tc.title.toLowerCase().includes(this.filterSearch.toLowerCase()) ||
        tc.use_case.toLowerCase().includes(this.filterSearch.toLowerCase()) ||
        (tc.actor && tc.actor.toLowerCase().includes(this.filterSearch.toLowerCase()));

      const matchType = !this.filterType || tc.test_type === this.filterType;
      const matchStatus = !this.filterStatus || tc.status === this.filterStatus;
      const matchPriority = !this.filterPriority || tc.priority === this.filterPriority;
      const matchInjection = !this.filterInjection || tc.injection_id === this.filterInjection;

      return matchSearch && matchType && matchStatus && matchPriority && matchInjection;
    });
  }

  get filteredInjections(): FaultInjectionCatalogItem[] {
    if (this.selectedCategoryFilter === 'ALL') {
      return this.injections;
    }
    return this.injections.filter((inj) => inj.category === this.selectedCategoryFilter);
  }

  // Actions d'Exécution
  runSingle(testId: number): void {
    this.runningTestId = testId;
    this.errorMessage = null;
    this.testService.runSingleTest(testId).subscribe({
      next: (res) => {
        this.runningTestId = null;
        this.loadTestCases();
        this.loadStats();
        this.showToast(
          res.passed
            ? `Test #${testId} validé avec succès (${res.test_run.duration_ms} ms)`
            : `Test #${testId} a échoué (${res.test_run.actual_behavior})`
        );
      },
      error: (err) => {
        this.runningTestId = null;
        this.errorMessage = err.message;
      }
    });
  }

  runAll(): void {
    this.isRunningAll = true;
    this.runAllProgress = 10;
    this.errorMessage = null;
    const ids = this.filteredTestCases.map((t) => t.id);

    this.testService.runAllTests(ids).subscribe({
      next: (summary: RunAllSummaryResponse) => {
        this.runAllProgress = 100;
        setTimeout(() => {
          this.isRunningAll = false;
          this.runAllProgress = 0;
        }, 600);
        this.loadTestCases();
        this.loadStats();
        this.showToast(
          `Exécution terminée : ${summary.passed}/${summary.total_executed} tests validés (${summary.duration_total_ms} ms).`
        );
      },
      error: (err) => {
        this.isRunningAll = false;
        this.errorMessage = err.message;
      }
    });
  }

  // Génération LLM
  generateWithAi(): void {
    if (!this.genDocText.trim()) return;
    this.isLoading = true;
    this.errorMessage = null;
    this.warningFallbackMessage = null;

    this.testService.generateTests(this.genDocText, this.genAnalysisName, this.genSaveToDb).subscribe({
      next: (res) => {
        this.isLoading = false;
        if (res.fallback_used) {
          this.warningFallbackMessage =
            "Attention : Le service Gemini était indisponible ou n'a pas répondu. Les cas de test ont été générés via le moteur de secours local (gabarits).";
        } else {
          this.showToast(`${res.total_generated} cas de test générés avec succès via Gemini !`);
        }
        this.loadTestCases();
        this.loadStats();
        this.activeTab = 'tests';
      },
      error: (err) => {
        this.isLoading = false;
        this.errorMessage = err.message;
      }
    });
  }

  // Détection d'anomalies
  detectAnomalies(): void {
    if (!this.genDocText.trim()) return;
    this.isDetecting = true;
    this.errorMessage = null;
    this.warningFallbackMessage = null;

    this.testService.detectAnomalies(this.genDocText, this.genAnalysisName, this.anoUseAi, this.anoGenerateTests, this.genSaveToDb).subscribe({
      next: (res) => {
        this.isDetecting = false;
        this.anomalyResult = res;
        if (res.fallback_used) {
          this.warningFallbackMessage =
            "Attention : Gemini était indisponible. Les anomalies ont été détectées par le moteur de règles local uniquement, sans validation IA.";
        } else {
          this.showToast(res.message);
        }
        if (res.generated_tests.length) {
          this.loadTestCases();
          this.loadStats();
        }
      },
      error: (err) => {
        this.isDetecting = false;
        this.errorMessage = err.message;
      }
    });
  }

  // Changement de statut manuel
  toggleStatus(test: TestCase): void {
    const nextStatusMap: Record<string, 'a_faire' | 'passe' | 'echoue'> = {
      a_faire: 'passe',
      passe: 'echoue',
      echoue: 'a_faire'
    };
    const nextStatus = nextStatusMap[test.status] || 'a_faire';

    this.testService.updateTestStatus(test.id, nextStatus).subscribe({
      next: () => {
        test.status = nextStatus;
        this.loadStats();
      },
      error: (err) => (this.errorMessage = err.message)
    });
  }

  // Exports
  exportMarkdown(): void {
    this.testService.exportTests('markdown').subscribe({
      next: (blob) => this.downloadBlob(blob, 'cahier_tests_robustesse.md'),
      error: (err) => (this.errorMessage = err.message)
    });
  }

  exportGherkin(): void {
    this.testService.exportTests('gherkin').subscribe({
      next: (blob) => this.downloadBlob(blob, 'gestion_tests.feature'),
      error: (err) => (this.errorMessage = err.message)
    });
  }

  private downloadBlob(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  // Modals et Formulaires
  openCreateModal(): void {
    this.isEditing = false;
    this.currentTest = this.getEmptyTestCase();
    this.showEditModal = true;
  }

  openEditModal(test: TestCase): void {
    this.isEditing = true;
    this.currentTest = JSON.parse(JSON.stringify(test));
    this.showEditModal = true;
  }

  closeEditModal(): void {
    this.showEditModal = false;
    this.currentTest = this.getEmptyTestCase();
  }

  addStep(): void {
    if (this.newStepInput.trim()) {
      if (!this.currentTest.steps) this.currentTest.steps = [];
      this.currentTest.steps.push(this.newStepInput.trim());
      this.newStepInput = '';
    }
  }

  removeStep(index: number): void {
    if (this.currentTest.steps) {
      this.currentTest.steps.splice(index, 1);
    }
  }

  saveTest(): void {
    if (!this.currentTest.title || !this.currentTest.use_case) return;

    if (this.isEditing && this.currentTest.id) {
      this.testService.updateTestCase(this.currentTest.id, this.currentTest).subscribe({
        next: () => {
          this.closeEditModal();
          this.loadTestCases();
          this.loadStats();
          this.showToast('Cas de test mis à jour.');
        },
        error: (err) => (this.errorMessage = err.message)
      });
    } else {
      this.testService.createTestCase(this.currentTest).subscribe({
        next: () => {
          this.closeEditModal();
          this.loadTestCases();
          this.loadStats();
          this.showToast('Nouveau cas de test créé.');
        },
        error: (err) => (this.errorMessage = err.message)
      });
    }
  }

  deleteTest(testId: number): void {
    if (confirm(`Confirmez-vous la suppression du test #${testId} ?`)) {
      this.testService.deleteTestCase(testId).subscribe({
        next: () => {
          this.loadTestCases();
          this.loadStats();
          this.showToast(`Test #${testId} supprimé.`);
        },
        error: (err) => (this.errorMessage = err.message)
      });
    }
  }

  // Historique des Runs
  viewRuns(test: TestCase): void {
    this.activeTestForRuns = test;
    this.testService.getTestRuns(test.id).subscribe({
      next: (runs) => {
        this.selectedTestRuns = runs;
        this.showRunsModal = true;
      },
      error: (err) => (this.errorMessage = err.message)
    });
  }

  closeRunsModal(): void {
    this.showRunsModal = false;
    this.activeTestForRuns = null;
    this.selectedTestRuns = [];
  }

  private getEmptyTestCase(): Partial<TestCase> {
    return {
      analysis_name: 'Système UML',
      use_case: '',
      actor: '',
      title: '',
      test_type: 'nominal',
      injection_id: null,
      preconditions: '',
      steps: ['Soumettre le diagramme au pipeline.'],
      expected_result: 'Documentation technique produite.',
      expected_behavior: 'traitement_normal',
      priority: 'moyenne',
      status: 'a_faire',
      generated_by_llm: false
    };
  }

  private showToast(msg: string): void {
    this.successMessage = msg;
    setTimeout(() => {
      if (this.successMessage === msg) this.successMessage = null;
    }, 4000);
  }
}
