import { Component, Input, OnChanges, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { marked } from 'marked';

@Component({
  selector: 'app-documentation-viewer',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './documentation-viewer.component.html'
})
export class DocumentationViewerComponent implements OnChanges {
  // Matched exactly to the API response key per your request
  @Input() documentation_markdown: string = '';
  
  parsedHtml: string = '';

  async ngOnChanges() {
    if (this.documentation_markdown) {
      // Parse markdown to HTML securely
      this.parsedHtml = await marked.parse(this.documentation_markdown);
    }
  }
  
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
