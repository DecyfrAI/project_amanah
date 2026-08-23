/** Headlines that rotate on the post-login hold. */
export const ENTRY_HEADLINES = [
  'Insights await',
  'Reading the monitored sample',
  'Opening the workspace',
] as const;

/**
 * Short how-to lines for the dashboard. Domain language stays cautious:
 * classifications are likely, not findings, and gaps are never zeros.
 */
export const ENTRY_TIPS = [
  'Every rate shows its numerator, its denominator, and whether collection covered the day.',
  'Filters live in the address bar, so a view can be shared without rewriting it.',
  'A missing collection day is a gap, not a quiet day drawn as zero.',
  'Open Explorer from a figure to read the reviewed examples behind it.',
  'The question mark beside a figure explains what it measures. Colour is never the only cue.',
  'Ask Amanah, in the corner, cites stored numbers. It will not invent a figure.',
  'Start an insight from a day, a key figure, or a breakdown row.',
] as const;
