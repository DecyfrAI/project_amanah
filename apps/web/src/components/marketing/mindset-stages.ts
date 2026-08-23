export interface MindsetStage {
  readonly id: string;
  readonly number: string;
  readonly name: string;
  readonly quote: string;
  readonly summary: string;
}

/**
 * Randy Borum's four-stage model (2003), paraphrased for this product.
 *
 * This is a published account of how some people move from a grievance toward
 * devaluing a target. It is not Amanah data, not a claim that every poster
 * follows the path, and not a claim that a comment caused an attack.
 */
export const MINDSET_STAGES: readonly MindsetStage[] = [
  {
    id: 'grievance',
    number: '1',
    name: 'Grievance',
    quote: "It's not right",
    summary:
      'A wrong is named. The feeling can be real, inherited, or taught. A grievance is not yet a target.',
  },
  {
    id: 'injustice',
    number: '2',
    name: 'Injustice',
    quote: "It's not fair",
    summary:
      'The wrong is framed as something done to a group the person identifies with. The story becomes moral, not only personal.',
  },
  {
    id: 'attribution',
    number: '3',
    name: 'Target attribution',
    quote: "It's your fault",
    summary:
      'Responsibility is assigned to a people, a faith, or a type of stranger. Hostility now has an address.',
  },
  {
    id: 'devaluation',
    number: '4',
    name: 'Distancing / devaluation',
    quote: "You're evil",
    summary:
      'The target is placed outside ordinary moral concern. Distance makes cruelty cheaper to say, and cheaper to cheer.',
  },
] as const;

export const MINDSET_CITATION = {
  label: 'Randy Borum, Understanding the Terrorist Mindset, FBI Law Enforcement Bulletin, 2003',
  href: 'https://leb.fbi.gov/file-repository/archives/july03leb.pdf',
} as const;
