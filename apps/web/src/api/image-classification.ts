import type {
  ConfidenceTier,
  ImageClassification,
  ImageExample,
  ImageExampleList,
} from './contracts';
import { ImageClassificationSchema, ImageExampleListSchema } from './contracts';

import itemsJson from '@/fixtures/meme-datapack/items.json' with { type: 'json' };
import manifestJson from '@/fixtures/meme-datapack/manifest.json' with { type: 'json' };

const DISCLOSURE =
  'Fixture classification. The stub did not read pixels, did not OCR the file, and did not send the image anywhere. A live service would classify after an upload to object storage.';

export function confidenceTier(score: number): ConfidenceTier {
  if (score >= 0.85) {
    return 'high';
  }
  if (score >= 0.6) {
    return 'medium';
  }
  return 'low';
}

export function loadImageExampleList(
  dataMode: ImageExampleList['data_mode'] = 'fixture',
): ImageExampleList {
  return ImageExampleListSchema.parse({
    data_mode: dataMode,
    manifest: {
      dataset_provider: manifestJson.dataset_provider,
      dataset_name: manifestJson.dataset_name,
      dataset_version: manifestJson.dataset_version,
      license_identifier: manifestJson.license_identifier,
      schema_mapping_version: manifestJson.schema_mapping_version,
      approval_state: manifestJson.approval_state,
      reviewer: manifestJson.reviewer,
    },
    items: itemsJson.items,
  });
}

export function imageExamples(): readonly ImageExample[] {
  return loadImageExampleList().items;
}

function hashName(value: string): number {
  let hash = 0;
  for (const char of value) {
    hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  }
  return hash;
}

function filenameLooksLike(itemId: string, filename: string): boolean {
  const dashed = itemId.replaceAll('_', '-');
  return filename.includes(itemId) || filename.includes(dashed);
}

export function pickImageExample(filename: string, exampleId?: string): ImageExample {
  const catalog = imageExamples();
  if (exampleId !== undefined) {
    const match = catalog.find((item) => item.id === exampleId);
    if (match !== undefined) {
      return match;
    }
  }
  const named = catalog.find((item) => filenameLooksLike(item.id, filename));
  if (named !== undefined) {
    return named;
  }
  return catalog[hashName(filename) % catalog.length]!;
}

export function classificationFromExample(
  example: ImageExample,
  dataMode: ImageClassification['data_mode'] = 'fixture',
): ImageClassification {
  const annotation = example.dataset_annotation;
  return ImageClassificationSchema.parse({
    data_mode: dataMode,
    example_id: example.id,
    relevance: 'muslim_related',
    stance: 'likely_anti_muslim',
    classification: 'likely_hate',
    hate_types: annotation.hate_types,
    severity: annotation.severity,
    narrative_tags: example.narrative_tags,
    score: example.score,
    confidence_tier: confidenceTier(example.score),
    rationale: example.rationale,
    model_name: 'amanah-image-stub',
    model_version: 'fixture-0.1',
    taxonomy_version: 'taxonomy-v2-spec-9.5',
    review_required: annotation.severity >= 3,
    dataset_annotation: annotation,
    status: 'classified_not_reviewed',
    disclosure: DISCLOSURE,
  });
}

export function classifyEvidenceFixture(input: {
  readonly image_filename: string;
  readonly example_id?: string;
}): ImageClassification {
  return classificationFromExample(pickImageExample(input.image_filename, input.example_id));
}
