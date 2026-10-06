import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DiagramUploaderComponent } from './components/diagram-uploader/diagram-uploader.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, DiagramUploaderComponent],
  template: `
    <main class="min-h-screen bg-gray-50 flex flex-col items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <app-diagram-uploader class="w-full"></app-diagram-uploader>
    </main>
  `
})
export class AppComponent {
  title = 'frontend';
}
