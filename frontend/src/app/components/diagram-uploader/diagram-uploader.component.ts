import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import {
  DiagramService,
  DiagramDocumentationResponse
} from '../../services/diagram.service';

import {
  PromptService,
  Prompt
} from '../../services/prompt.service';

import {
  UMLReviewResponse,
  UmlReviewService
} from '../../services/uml-review.service';

import { DocumentationViewerComponent } from '../documentation-viewer/documentation-viewer.component';
import { UmlReviewViewerComponent } from '../uml-review-viewer/uml-review-viewer.component';


@Component({
  selector: 'app-diagram-uploader',
  standalone: true,

  imports: [
    CommonModule,
    FormsModule,
    DocumentationViewerComponent,
    UmlReviewViewerComponent
  ],

  template: `
    <div
      class="max-w-3xl mx-auto mt-10 p-8 bg-white/70 backdrop-blur-xl rounded-3xl
             shadow-[0_8px_30px_rgb(0,0,0,0.08)] border border-gray-100">

      <!-- HEADER -->
      <div class="text-center mb-10">

        <h2
          class="text-4xl font-extrabold bg-clip-text text-transparent
                 bg-gradient-to-r from-blue-600 to-indigo-500">

          Architecture Analyzer

        </h2>

        <p class="text-gray-500 mt-3 font-medium">
          Drop a UML diagram here.
          Let AI generate your markdown documentation.
        </p>

      </div>


      <!-- UPLOAD -->
      <div
        class="relative flex flex-col items-center justify-center
               w-full h-72 border-2 border-dashed rounded-2xl
               transition-all duration-300 ease-out overflow-hidden
               group cursor-pointer"

        [class.border-indigo-500]="isDragging"
        [class.bg-indigo-50]="isDragging"

        [class.border-gray-300]="!isDragging"
        [class.bg-gray-50]="!isDragging"

        [class.pointer-events-none]="isLoading"
        [class.opacity-60]="isLoading"

        (dragover)="onDragOver($event)"
        (dragleave)="onDragLeave($event)"
        (drop)="onDrop($event)"
        (click)="fileInput.click()">


        <input
          #fileInput
          type="file"
          class="hidden"
          accept="image/png, image/jpeg, image/webp"
          (change)="onFileSelected($event)"
          [disabled]="isLoading">


        <div
          class="flex flex-col items-center justify-center
                 p-6 text-center transform
                 transition-transform duration-300
                 group-hover:scale-105">

          <svg
            class="w-16 h-16 mb-4 text-gray-400
                   group-hover:text-indigo-500
                   transition-colors duration-300"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg">

            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12">
            </path>

          </svg>


          <ng-container *ngIf="!selectedFile; else fileSelectedTpl">

            <p class="mb-2 text-lg text-gray-600">

              <span class="font-bold text-indigo-600">
                Click to upload
              </span>

              or drag and drop

            </p>

            <p class="text-sm text-gray-400 font-medium">
              PNG, JPG or WEBP (Max 10MB)
            </p>

          </ng-container>


          <ng-template #fileSelectedTpl>

            <div
              class="flex items-center px-4 py-2
                     bg-indigo-100 rounded-full">

              <svg
                class="w-5 h-5 text-indigo-600 mr-2"
                fill="currentColor"
                viewBox="0 0 20 20">

                <path
                  fill-rule="evenodd"
                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                  clip-rule="evenodd">
                </path>

              </svg>

              <span
                class="text-indigo-700 font-bold
                       truncate max-w-[200px]">

                {{ selectedFile!.name }}

              </span>

            </div>

          </ng-template>

        </div>

      </div>


      <!-- GESTION DES PROMPTS -->
      <div
        *ngIf="prompts.length > 0"
        class="mt-8">

        <label
          class="block text-sm font-bold
                 text-gray-700 mb-2">

          Prompt à utiliser

        </label>


        <select
          [(ngModel)]="selectedPromptId"
          [disabled]="isLoading"

          class="w-full px-4 py-3 rounded-xl
                 border border-gray-300
                 bg-white font-medium text-gray-700
                 focus:outline-none
                 focus:ring-2 focus:ring-indigo-500">

          <option
            *ngFor="let prompt of prompts"
            [ngValue]="prompt.id">

            {{ prompt.name }}
            {{ prompt.is_default ? ' (par défaut)' : '' }}

          </option>

        </select>

      </div>


      <!-- GENERATE DOCUMENTATION -->
      <button
        (click)="generateDocumentation()"

        [disabled]="!selectedFile || isLoading"

        class="relative w-full mt-8 py-4 px-6
               rounded-2xl font-bold text-lg text-white
               transition-all duration-300 overflow-hidden
               shadow-[0_4px_14px_0_rgb(99,102,241,0.39)]
               hover:shadow-[0_6px_20px_rgba(99,102,241,0.5)]
               active:scale-[0.98]
               disabled:opacity-50
               disabled:cursor-not-allowed
               disabled:active:scale-100
               disabled:shadow-none
               bg-gradient-to-r from-blue-600 to-indigo-600
               hover:from-blue-500 hover:to-indigo-500">

        <div
          class="flex items-center
                 justify-center space-x-3">

          <svg
            *ngIf="isLoading"
            class="animate-spin h-6 w-6 text-white"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24">

            <circle
              class="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              stroke-width="4">
            </circle>

            <path
              class="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373
                 0 0 5.373 0 12h4zm2
                 5.291A7.962 7.962 0
                 014 12H0c0 3.042
                 1.135 5.824 3 7.938l3-2.647z">
            </path>

          </svg>


          <span>

            {{
              isLoading
                ? 'Analyzing Architecture...'
                : 'Generate Documentation'
            }}

          </span>

        </div>

      </button>


      <!-- ERROR DOCUMENTATION -->
      <div
        *ngIf="errorMessage"

        class="mt-6 p-4 border-l-4
               border-red-500 bg-red-50
               text-red-700 rounded-r-lg
               animate-fade-in-up font-medium">

        {{ errorMessage }}

      </div>


      <!-- DOCUMENTATION RESULT -->
      <div
        *ngIf="result"

        class="mt-10 p-8 bg-gray-50
               rounded-2xl border border-gray-200
               animate-fade-in-up shadow-inner">


        <h3
          class="text-2xl font-black
                 text-gray-800 mb-3">

          {{ result.system_title }}

        </h3>


        <!-- PROMPT UTILISE -->
        <p
          *ngIf="result.prompt_name"
          class="mb-3 text-sm text-gray-500">

          Prompt utilisé :

          <span
            class="font-bold text-indigo-700">

            {{ result.prompt_name }}

          </span>

        </p>


        <!-- ACTEURS -->
        <div class="flex items-start mb-6">

          <span
            class="inline-flex items-center
                   px-3 py-1 rounded-full
                   text-xs font-bold
                   bg-indigo-100 text-indigo-800">

            Acteurs Détectés:
            {{ result.detected_actors.length }}

          </span>


          <p
            class="ml-3 text-sm font-medium
                   text-gray-600 mt-0.5">

            {{ result.detected_actors.join(', ') }}

          </p>

        </div>


        <!-- MARKDOWN DOCUMENTATION -->
        <app-documentation-viewer
          [documentation_markdown]="result.documentation_markdown">
        </app-documentation-viewer>


        <!-- UML REVIEW BUTTON -->
        <button
          type="button"

          (click)="reviewDocumentation()"

          [disabled]="isReviewLoading || hasInvalidDocumentation"

          class="mt-6 w-full rounded-xl
                 bg-indigo-600 px-5 py-3
                 font-bold text-white
                 transition hover:bg-indigo-700
                 disabled:cursor-not-allowed
                 disabled:opacity-60">

          {{
            isReviewLoading
              ? "Analyse UML en cours..."
              : reviewResult || reviewErrorMessage
                ? "Relancer l'analyse"
                : "Analyser la qualité UML"
          }}

        </button>


        <!-- INVALID DOCUMENTATION -->
        <div
          *ngIf="hasInvalidDocumentation"

          role="status"

          class="mt-4 rounded-lg
                 border-l-4 border-amber-500
                 bg-amber-50 p-4
                 font-medium text-amber-800">

          Impossible d'analyser la qualité UML
          car la documentation n'a pas pu être générée.

        </div>


        <!-- REVIEW ERROR -->
        <div
          *ngIf="reviewErrorMessage"

          role="alert"

          class="mt-4 rounded-lg
                 border-l-4 border-red-500
                 bg-red-50 p-4
                 font-medium text-red-700">

          {{ reviewErrorMessage }}

        </div>


        <!-- UML REVIEW RESULT -->
        <app-uml-review-viewer
          *ngIf="reviewResult"
          [review]="reviewResult">
        </app-uml-review-viewer>

      </div>

    </div>
  `,


  styles: [`

    @keyframes fadeInUp {

      from {
        opacity: 0;
        transform: translateY(15px);
      }

      to {
        opacity: 1;
        transform: translateY(0);
      }

    }


    .animate-fade-in-up {

      animation:
        fadeInUp
        0.5s
        cubic-bezier(0.16, 1, 0.3, 1)
        forwards;

    }

  `]

})


export class DiagramUploaderComponent implements OnInit {

  private diagramService = inject(DiagramService);

  // Gestion des Prompts
  private promptService = inject(PromptService);

  // Gestion UML Review
  private umlReviewService = inject(UmlReviewService);


  isDragging = false;

  isLoading = false;

  isReviewLoading = false;


  selectedFile: File | null = null;


  errorMessage = '';

  reviewErrorMessage = '';


  result: DiagramDocumentationResponse | null = null;

  reviewResult: UMLReviewResponse | null = null;


  // Gestion des Prompts
  prompts: Prompt[] = [];

  selectedPromptId: number | null = null;



  ngOnInit() {

    this.promptService.getAll().subscribe({

      next: (prompts) => {

        this.prompts = prompts;

        this.selectedPromptId =
          prompts.find(
            prompt => prompt.is_default
          )?.id ?? null;

      },

      error: () => {

        this.prompts = [];

      }

    });

  }



  get hasInvalidDocumentation(): boolean {

    if (!this.result) {

      return true;

    }


    const markdown =
      this.result.documentation_markdown.trim();


    if (!markdown) {

      return true;

    }


    const hasOcrText =
      this.result.ocr_snippets?.some(
        snippet =>
          snippet.text?.trim()
      );


    if (!hasOcrText) {

      return true;

    }


    const normalizedMarkdown =
      markdown.toLocaleLowerCase();


    if (

      normalizedMarkdown.includes(
        'aucun texte détecté'
      )

      ||

      normalizedMarkdown.includes(
        'erreur s’est produite lors de la génération'
      )

      ||

      normalizedMarkdown.includes(
        "erreur s'est produite lors de la génération"
      )

      ||

      normalizedMarkdown.includes(
        'erreur génération'
      )

      ||

      normalizedMarkdown.includes(
        'failed to generate documentation'
      )

    ) {

      return true;

    }


    const containsActors =
      /acteur|acteurs/i.test(markdown);


    const containsUseCases =
      /cas d['’]utilisation|use[- ]case/i
        .test(markdown);


    return !containsActors || !containsUseCases;

  }



  onDragOver(event: DragEvent) {

    event.preventDefault();

    event.stopPropagation();

    this.isDragging = true;

  }



  onDragLeave(event: DragEvent) {

    event.preventDefault();

    event.stopPropagation();

    this.isDragging = false;

  }



  onDrop(event: DragEvent) {

    event.preventDefault();

    event.stopPropagation();

    this.isDragging = false;


    const files =
      event.dataTransfer?.files;


    if (files && files.length > 0) {

      this.handleFile(files[0]);

    }

  }



  onFileSelected(event: Event) {

    const input =
      event.target as HTMLInputElement;


    if (
      input.files
      &&
      input.files.length > 0
    ) {

      this.handleFile(
        input.files[0]
      );

    }

  }



  private handleFile(file: File) {

    const validTypes = [

      'image/jpeg',

      'image/png',

      'image/webp'

    ];


    if (
      !validTypes.includes(file.type)
    ) {

      this.errorMessage =
        'Format invalide. Veuillez importer une image (JPEG, PNG, WebP).';


      this.selectedFile = null;

      return;

    }


    this.errorMessage = '';

    this.reviewErrorMessage = '';


    this.selectedFile = file;


    this.result = null;

    this.reviewResult = null;

  }



  generateDocumentation() {

    if (!this.selectedFile) {

      return;

    }


    this.isLoading = true;


    this.errorMessage = '';

    this.reviewErrorMessage = '';


    this.result = null;

    this.reviewResult = null;


    /*
     * IMPORTANT :
     * On conserve selectedPromptId
     * pour ne pas casser la Gestion
     * des Prompts du collègue.
     */
    this.diagramService
      .uploadDiagram(
        this.selectedFile,
        this.selectedPromptId
      )
      .subscribe({

        next: (response) => {

          this.result = response;

          this.isLoading = false;

        },


        error: (err: Error) => {

          this.errorMessage =
            err.message;


          this.isLoading = false;

          this.selectedFile = null;

        }

      });

  }



  reviewDocumentation() {

    if (

      !this.result?.documentation_markdown

      ||

      this.hasInvalidDocumentation

      ||

      this.isReviewLoading

    ) {

      return;

    }


    this.isReviewLoading = true;


    this.reviewErrorMessage = '';


    this.reviewResult = null;


    this.umlReviewService

      .reviewDocumentation(
        this.result.documentation_markdown
      )

      .subscribe({

        next: (response) => {

          this.reviewResult =
            response;


          this.isReviewLoading =
            false;

        },


        error: (err: Error) => {

          this.reviewErrorMessage =
            err.message;


          this.isReviewLoading =
            false;

        }

      });

  }

}