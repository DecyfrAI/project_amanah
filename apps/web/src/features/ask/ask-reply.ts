import type { AssistantReply, ExplorerItem, NewsItem, Overview } from '@/api/contracts';
import { hateTypeLabel, platformLabel, reviewLabel } from '@/api/fixture-derive';
import { dailyRate, formatDay, formatRate } from '@/components/charts/rate';

const LIMITATIONS = [
  'Numbers in this answer come from the stored figures for the current window, not from a generated estimate.',
  'A later retrieval step may pull methodology text and stored briefs as context. It will not be allowed to invent a rate or treat a collection gap as zero.',
] as const;

export interface AskReplyContext {
  readonly news: readonly NewsItem[];
  readonly items: readonly ExplorerItem[];
}

const EMPTY_CONTEXT: AskReplyContext = { news: [], items: [] };

function peakCollectedDay(overview: Overview) {
  let peak: (typeof overview.daily)[number] | null = null;
  let peakValue = -1;
  for (const day of overview.daily) {
    const value = dailyRate(day);
    if (value !== null && value > peakValue) {
      peak = day;
      peakValue = value;
    }
  }
  return peak === null ? null : { day: peak, rate: peakValue };
}

/**
 * Builds a grounded reply from the same overview the dashboard already shows.
 *
 * The model never supplies a number here. Matching is coarse on purpose: if the
 * question does not name a figure we can cite, we say so rather than guessing.
 */
export function replyFromOverview(
  question: string,
  overview: Overview,
  context: AskReplyContext = EMPTY_CONTEXT,
): AssistantReply {
  const asked = question.toLowerCase();
  const rate = overview.metrics.find((metric) => metric.id === 'rate');
  const reviewed = overview.metrics.find((metric) => metric.id === 'reviewed');
  const byType = overview.breakdowns.find((entry) => entry.id === 'by-type');

  if (
    /\b(how|method|mean|confidence|model)\b/.test(asked) &&
    !/\b(rate|percent|hate)\b/.test(asked)
  ) {
    return {
      answer:
        'Classified as likely anti-Muslim hate is a model score, not a finding that something is hate, until a person reviews it. Relevance is separate from hate: Muslim vocabulary never colours an item as harmful. Every rate on this product carries its numerator, denominator, and collection coverage.',
      citations: [
        {
          kind: 'methodology',
          id: 'method_stance',
          label: 'Stance labels and review model',
        },
      ],
      limitations: [...LIMITATIONS],
      groundedIn: 'methodology',
    };
  }

  if (
    /\b(cover|sample|collected|gap)\b/.test(asked) &&
    !/\b(news|coincid|entry|move|moved|trend)\b/.test(asked)
  ) {
    const gapNote =
      overview.coverage.warnings.length === 0
        ? 'No coverage warning is attached to this window.'
        : overview.coverage.warnings.join(' ');

    return {
      answer: `This view covers ${overview.window.from} to ${overview.window.to} (${overview.window.timezone}). ${overview.coverage.itemsRelevant.toLocaleString('en-GB')} Muslim-related items of ${overview.coverage.itemsObserved.toLocaleString('en-GB')} observed, from ${overview.coverage.sources.join(', ')}. ${gapNote}`,
      citations: [
        {
          kind: 'coverage',
          id: 'coverage',
          label: `${overview.window.from} to ${overview.window.to}`,
        },
      ],
      limitations: [...LIMITATIONS],
      groundedIn: 'figures',
    };
  }

  if (/\b(news|headline|current event|coincid|correlation|associated with)\b/.test(asked)) {
    const peak = peakCollectedDay(overview);
    const headlines =
      context.news.length === 0
        ? 'No news items are attached to this fixture window.'
        : `News in this window includes ${context.news
            .slice(0, 2)
            .map((item) => `"${item.title}" (${item.source_name})`)
            .join(', ')}.`;
    const movement =
      peak === null || peak.day.likelyHate === null || peak.day.relevant === null
        ? 'No collected day in this window has a rate that can be stated.'
        : `The highest collected daily rate in the sample is ${formatRate(peak.rate)} on ${formatDay(peak.day.date)} (${peak.day.likelyHate.toLocaleString('en-GB')} of ${peak.day.relevant.toLocaleString('en-GB')} Muslim-related items).`;

    return {
      answer: `${headlines} Those articles are coinciding context. Amanah did not classify them, and a shared date is not a cause. ${movement}`,
      citations: [
        {
          kind: 'coverage',
          id: 'coverage',
          label: `${overview.window.from} to ${overview.window.to}`,
        },
      ],
      limitations: [...LIMITATIONS],
      groundedIn: 'figures',
    };
  }

  if (/\b(trend|move|moved|over time|daily)\b/.test(asked)) {
    const peak = peakCollectedDay(overview);
    const gapCount = overview.daily.filter((day) => !day.collected).length;
    if (peak === null || peak.day.likelyHate === null || peak.day.relevant === null) {
      return cannotCite(overview);
    }
    const gapNote =
      gapCount === 0
        ? 'Every day in this window was collected.'
        : `${gapCount === 1 ? '1 day in this window was' : `${String(gapCount)} days in this window were`} not collected and stay a gap, not a rate of zero.`;

    return {
      answer: `Inside this monitored sample the highest collected daily rate is ${formatRate(peak.rate)} on ${formatDay(peak.day.date)} (${peak.day.likelyHate.toLocaleString('en-GB')} of ${peak.day.relevant.toLocaleString('en-GB')} Muslim-related items). ${gapNote} That is movement inside the sample, not a causal claim.`,
      citations: [
        {
          kind: 'metric',
          id: 'rate',
          label: 'Daily likely hate rate',
        },
      ],
      limitations: [...LIMITATIONS],
      groundedIn: 'figures',
    };
  }

  if (/\b(entry|entries|explorer|a post|one post)\b/.test(asked)) {
    const item = context.items[0];
    if (item === undefined) {
      return cannotCite(overview);
    }
    const typeNote =
      item.hateType === null ? 'no hate type assigned' : hateTypeLabel(item.hateType);
    const classNote =
      item.classification === null
        ? 'not yet classified'
        : item.classification === 'likely_hate'
          ? 'classified as likely anti-Muslim hate'
          : 'classified as not hate';
    const scoreNote =
      item.modelScore === null
        ? 'It has no model score yet.'
        : `The model score is ${item.modelScore.toFixed(2)}, not a measure of certainty.`;

    return {
      answer: `One Explorer row from this sample is ${item.id} (${platformLabel(item.platform)}, ${item.date}). Container: ${item.containerTitle ?? 'no public context'}. It is ${classNote}, ${typeNote}, ${reviewLabel(item.reviewState)}. ${scoreNote} There is no author field.`,
      citations: [
        {
          kind: 'coverage',
          id: 'coverage',
          label: `${overview.window.from} to ${overview.window.to}`,
        },
      ],
      limitations: [...LIMITATIONS],
      groundedIn: 'figures',
    };
  }

  if (
    /\b(type|narrative|threat|composition|share|made of)\b/.test(asked) &&
    byType !== undefined &&
    byType.rows[0] !== undefined
  ) {
    const top = byType.rows.toSorted((left, right) => right.count - left.count)[0];
    if (top === undefined) {
      return cannotCite(overview);
    }
    const share = byType.total === 0 ? 0 : top.count / byType.total;

    return {
      answer: `Among items classified as likely hate in this window, ${top.label} is the largest named share: ${top.count.toLocaleString('en-GB')} of ${byType.total.toLocaleString('en-GB')} (${formatRate(share)}). That is a composition of the monitored sample, not a claim about a whole platform.`,
      citations: [
        {
          kind: 'metric',
          id: byType.id,
          label: byType.label,
        },
      ],
      limitations: [...LIMITATIONS],
      groundedIn: 'figures',
    };
  }

  if (
    /\b(review|confirm|confirmed)\b/.test(asked) &&
    reviewed?.numerator !== null &&
    reviewed?.denominator !== null &&
    reviewed !== undefined
  ) {
    return {
      answer: `${reviewed.label}: ${reviewed.numerator.toLocaleString('en-GB')} of ${reviewed.denominator.toLocaleString('en-GB')}. A review decision appends beside the model output. It never overwrites it.`,
      citations: [
        {
          kind: 'metric',
          id: reviewed.id,
          label: reviewed.label,
        },
      ],
      limitations: [...LIMITATIONS],
      groundedIn: 'figures',
    };
  }

  if (
    rate !== undefined &&
    rate.numerator !== null &&
    rate.denominator !== null &&
    (/\b(rate|percent|percentage|hate)\b/.test(asked) || asked.includes('likely'))
  ) {
    return {
      answer: `${rate.label}: ${formatRate(rate.value)} (${rate.numerator.toLocaleString('en-GB')} of ${rate.denominator.toLocaleString('en-GB')} Muslim-related items) for ${overview.window.from} to ${overview.window.to}. That describes this monitored sample. It is not a prevalence estimate for any platform.`,
      citations: [
        {
          kind: 'metric',
          id: rate.id,
          label: rate.label,
        },
      ],
      limitations: [...LIMITATIONS],
      groundedIn: 'figures',
    };
  }

  return cannotCite(overview);
}

function cannotCite(overview: Overview): AssistantReply {
  return {
    answer: `I can only talk about figures already computed for ${overview.window.from} to ${overview.window.to}: coverage, the likely-hate rate and its daily movement, the composition of likely-hate items, a stored Explorer entry, coinciding news, and confirmed reviews. Ask about one of those. I will not invent a number that is not on the page.`,
    citations: [],
    limitations: [...LIMITATIONS],
    groundedIn: 'none',
  };
}
