import { hateTypeLabel, severityLabel, type ExplorerItem } from '@/api';

export function classificationLabel(classification: ExplorerItem['classification']): string {
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
