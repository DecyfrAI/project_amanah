export interface AskPrompt {
  readonly id: string;
  readonly label: string;
  readonly question: string;
}

/**
 * Starter questions for Ask Amanah.
 *
 * Each one names a figure or a stored item the fixture reply can cite. A live
 * assistant can keep the same chips and retrieve more context behind the same
 * contract. Person-level questions stay off this list.
 */
export const ASK_PROMPTS: readonly AskPrompt[] = [
  {
    id: 'rate',
    label: 'Likely-hate rate',
    question: 'What is the likely hate rate in this window?',
  },
  {
    id: 'trend',
    label: 'Trend over time',
    question: 'How did the likely-hate rate move over this window?',
  },
  {
    id: 'cover',
    label: 'Coverage',
    question: 'What does this sample cover, and where are the gaps?',
  },
  {
    id: 'entry',
    label: 'An explorer entry',
    question: 'Walk me through one explorer entry from this sample.',
  },
  {
    id: 'events',
    label: 'Current events',
    question: 'Which news items coincide with this window?',
  },
  {
    id: 'coincide',
    label: 'News and the rate',
    question: 'Does the news stream coincide with a change in the likely-hate rate?',
  },
];
