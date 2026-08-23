import { platformLabel, type Insight } from '@/api';
import type { StatusIndicator } from '@/components/ui/StatusPill';

export function insightSourceLine(insight: Insight): string {
  if (insight.coverage.sources.length === 0) {
    return 'No source recorded';
  }
  return insight.coverage.sources.map((source) => platformLabel(source)).join(', ');
}

export function insightKind(insight: Insight): { indicator: StatusIndicator; label: string } {
  if (insight.generation.model === 'viewer-snapshot') {
    return { indicator: 'ok', label: 'Snapshot from a figure' };
  }
  if (insight.generation.isMachineGenerated) {
    return { indicator: 'pending', label: 'Machine-generated' };
  }
  return { indicator: 'ok', label: 'Prepared by hand' };
}

export function insightProvenance(insight: Insight): string {
  if (insight.generation.model === 'viewer-snapshot') {
    return `Snapshot started from a figure, ${insight.generation.generatedAt}.`;
  }
  if (insight.generation.isMachineGenerated) {
    return `Machine-generated brief from ${insight.generation.model}, ${insight.generation.generatedAt}.`;
  }
  return `Brief prepared ${insight.generation.generatedAt}.`;
}
