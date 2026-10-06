import { Component, Input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MarkdownModule } from 'ngx-markdown';

@Component({
  selector: 'app-documentation-viewer',
  standalone: true,
  imports: [CommonModule, MarkdownModule],
  templateUrl: './documentation-viewer.component.html'
})
export class DocumentationViewerComponent {
  // Matched exactly to the API response key per your request
  @Input() documentation_markdown: string = '';
  
  isCopied = signal(false);

  async copyToClipboard() {
    if (!this.documentation_markdown) return;
    
    try {
      await navigator.clipboard.writeText(this.documentation_markdown);
      this.isCopied.set(true);
      setTimeout(() => this.isCopied.set(false), 2000);
    } catch (err) {
      console.error('Failed to copy: ', err);
    }
  }
}
