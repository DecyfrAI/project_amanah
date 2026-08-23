/**
 * Local download helper for a prepared report.
 *
 * Ordinary YouTube and Reddit reports go through official forms, not a public
 * mailbox, so this module does not build mailto or .eml output.
 */
export function downloadText(filename: string, contents: string, mime: string): void {
  const blob = new Blob([contents], { type: mime });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
