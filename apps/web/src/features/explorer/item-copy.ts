import { hateTypeLabel, severityLabel, type ExplorerItem } from '@/api';

export function classificationLabel(classification: ExplorerItem['classification']): string {
  if (classification === null) {
    // Collected but not yet analysed. Never "safe": absence of a prediction is
    // absence of knowledge, and the copy must not put words in the model's mouth.
    return 'Not yet classified';
  }
  return classification === 'likely_hate'
    ? 'Classified as likely anti-Muslim hate'
    : 'Not classified as hate';
}

export function itemTypeLabel(hateType: ExplorerItem['hateType']): string {
  return hateType === null ? 'Not applicable' : hateTypeLabel(hateType);
}

export function itemSeverityLabel(severity: ExplorerItem['severity']): string {
  if (severity === null) {
    return 'No severity recorded';
  }
  return severityLabel(String(severity));
}
