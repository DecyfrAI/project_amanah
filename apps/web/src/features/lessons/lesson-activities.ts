/**
 * Per-module exercises for the Lessons reader.
 *
 * Each activity is local data, tied to that module’s thesis. None of this is an
 * Amanah finding, a person-level score, or a claim that speech caused an act.
 */

export type PyramidBucket = 'opinion' | 'action';
export type RoomVantage = 'inside' | 'outside';
export type RevealMode = 'lock' | 'inspect';

export interface LessonActivityPage {
  readonly id: string;
  readonly moduleId: string;
  readonly title: string;
  readonly afterChapterId: string;
}

export interface SortItem {
  readonly id: string;
  readonly statement: string;
  readonly bucket: PyramidBucket;
  readonly explanation: string;
}

export interface ChoiceOption {
  readonly id: string;
  readonly label: string;
  readonly correct: boolean;
  readonly explanation: string;
}

export interface ChoiceQuestion {
  readonly id: string;
  readonly prompt: string;
  readonly options: readonly ChoiceOption[];
}

export interface ChoiceActivityDef {
  readonly lead: string;
  readonly reveal: RevealMode;
  readonly questions: readonly ChoiceQuestion[];
  readonly table?: ScopedRateTable;
}

export interface ScopedRateTable {
  readonly caption: string;
  readonly rows: readonly ScopedRateRow[];
}

export interface ScopedRateRow {
  readonly id: string;
  readonly window: string;
  readonly labelled: string;
  readonly collected: string;
  readonly coverage: string;
  readonly isGap: boolean;
}

export interface StageRemark {
  readonly id: string;
  readonly remark: string;
  readonly stageId: 'grievance' | 'injustice' | 'attribution' | 'devaluation';
  readonly explanation: string;
}

export interface RoomVantageDef {
  readonly id: RoomVantage;
  readonly label: string;
  readonly cues: readonly string[];
  readonly reflection: string;
}

export interface PaperRound {
  readonly id: string;
  readonly paper: string;
  readonly prompt: string;
  readonly found: PaperCard;
  readonly overclaim: PaperCard;
}

export interface PaperCard {
  readonly id: string;
  readonly label: string;
  readonly explanation: string;
}

export const LESSON_ACTIVITY_PAGES: readonly LessonActivityPage[] = [
  {
    id: '01-activity',
    moduleId: '01',
    title: 'Exercise: opinion or action',
    afterChapterId: '01-what-for',
  },
  {
    id: '02-activity',
    moduleId: '02',
    title: 'Exercise: match the mechanism',
    afterChapterId: '02-group',
  },
  {
    id: '03-activity',
    moduleId: '03',
    title: 'Exercise: which stage is this remark?',
    afterChapterId: '03-four-movements',
  },
  {
    id: '04-activity',
    moduleId: '04',
    title: 'Exercise: in the room, or outside it',
    afterChapterId: '04-isolation',
  },
  {
    id: '05-activity',
    moduleId: '05',
    title: 'Exercise: what Conway and Gill support',
    afterChapterId: '05-tool',
  },
  {
    id: '06-activity',
    moduleId: '06',
    title: 'Exercise: what the paper found',
    afterChapterId: '06-imageboards',
  },
  {
    id: '07-activity',
    moduleId: '07',
    title: 'Exercise: can this coefficient travel?',
    afterChapterId: '07-no-import',
  },
  {
    id: '08-activity',
    moduleId: '08',
    title: 'Exercise: which sentence is allowed?',
    afterChapterId: '08-denominator',
  },
];

export const PYRAMID_LABELS: Record<PyramidBucket, string> = {
  opinion: 'Opinion pyramid',
  action: 'Action pyramid',
};

export const SORT_LEAD =
  'McCauley and Moskalenko split radicalization of opinion from radicalization of action. Sort each statement. A harsh view is not an act.';

export const SORT_ITEMS: readonly SortItem[] = [
  {
    id: 'sort-justified',
    statement: 'A person tells a survey that political violence is sometimes justified.',
    bucket: 'opinion',
    explanation:
      'That is a view on a questionnaire. It sits on the opinion pyramid. Most people who endorse a radical justification never join an illegal act.',
  },
  {
    id: 'sort-protest',
    statement: 'A person joins a legal demonstration after months of posting.',
    bucket: 'action',
    explanation:
      'Joining a demonstration is behaviour. It sits on the action pyramid, here at legal activism, not at violence.',
  },
  {
    id: 'sort-plot',
    statement: 'A person uses violence in a plot without a long public trail of posts.',
    bucket: 'action',
    explanation:
      'The act is on the action pyramid. The two-pyramids model allows action to move while the public opinion trail stays thin.',
  },
  {
    id: 'sort-duty',
    statement:
      'A person treats a harsh justification as a personal duty, and never leaves the thread.',
    bucket: 'opinion',
    explanation:
      'Duty-talk on a thread is still opinion. Sitting high on the opinion pyramid does not place anyone on the action pyramid.',
  },
];

export const MECHANISM_ACTIVITY: ChoiceActivityDef = {
  lead: 'McCauley and Moskalenko (2008) list mechanisms, not stages. Match each short vignette to the door it illustrates. A door is a possible path, not a prediction.',
  reveal: 'lock',
  questions: [
    {
      id: 'mech-love',
      prompt:
        'A person starts sitting in a circle because a partner they love is already there. They barely follow the arguments.',
      options: [
        {
          id: 'love',
          label: 'Joining through love or friendship',
          correct: true,
          explanation:
            'The 2008 inventory names love and friendship as an individual door. Ideology can stay thin while the bond does the moving.',
        },
        {
          id: 'victim',
          label: 'Personal victimization',
          correct: false,
          explanation:
            'Nothing in the vignette says the person was harmed. Victimization is a different door, and most harmed people never enter illegal action.',
        },
        {
          id: 'jujitsu',
          label: 'Jujitsu politics',
          correct: false,
          explanation:
            'Jujitsu politics is a group strategy: invite a harsh response so bystanders swing toward the movement. This vignette is about a bond, not a tactic.',
        },
      ],
    },
    {
      id: 'mech-isolation',
      prompt:
        'A circle that used to argue now talks only to itself. Dissenters leave. The remaining jokes get harder.',
      options: [
        {
          id: 'isolation',
          label: 'Group isolation',
          correct: true,
          explanation:
            'Isolation is a group mechanism: a room that talks only to itself can treat cruelty as ordinary work. It is not a claim that this circle will act.',
        },
        {
          id: 'grievance',
          label: 'Personal political grievance',
          correct: false,
          explanation:
            'A grievance can open an individual door. The vignette is about the room’s boundary, not one person’s complaint.',
        },
        {
          id: 'slope',
          label: 'Slippery-slope joining',
          correct: false,
          explanation:
            'Slippery-slope joining is an individual path into a group. Here the change is the group filtering itself.',
        },
      ],
    },
  ],
};

export const STAGE_LEAD =
  'Borum’s 2003 sketch is a heuristic for how a grievance can be retargeted. Pick the stage each synthetic remark is closest to. A remark is not a path, and it did not produce an attack.';

export const STAGE_REMARKS: readonly StageRemark[] = [
  {
    id: 'stage-factory',
    remark: 'The factory closing was not right.',
    stageId: 'grievance',
    explanation:
      'A wrong is named. That is the first movement. A grievance is not yet a target, and it is not a forecast.',
  },
  {
    id: 'stage-help',
    remark: 'Our street never gets the help that other families get.',
    stageId: 'injustice',
    explanation:
      'The wrong is recast as unfairness done to a we. The story has become moral, not only personal.',
  },
  {
    id: 'stage-blame',
    remark: 'Every person from that group is the reason things got worse.',
    stageId: 'attribution',
    explanation:
      'Blame is assigned to a type of stranger. Hostility now has an address. Collective blame is still a remark, not an act.',
  },
  {
    id: 'stage-outside',
    remark: 'Those people sit outside ordinary care. They are not like us.',
    stageId: 'devaluation',
    explanation:
      'The target is placed outside moral concern. The sketch names that movement. It does not say the speaker will act, and it does not classify anyone in a feed.',
  },
];

export const ROOM_LEAD =
  'Toggle the vantage. Isolation and social identity can teach a circle that cruelty is ordinary. This is a reflection, not a diagnosis and not a score.';

export const ROOM_VANTAGES: readonly RoomVantageDef[] = [
  {
    id: 'inside',
    label: 'In the room',
    cues: [
      'Replies that reward extremity are the ones that survive.',
      'Dissent starts to sound like betrayal.',
      'The middle of the circle has already moved.',
    ],
    reflection:
      'From inside, harder jokes can feel like ordinary work. That is a social setting, not a test of a person. Many isolated rooms stay dull. The mechanism is a possible teacher, not a verdict.',
  },
  {
    id: 'outside',
    label: 'Outside the room',
    cues: [
      'A neighbour who never joined the thread.',
      'A shop queue where the same line does not land.',
      'A family table that still expects care for a stranger.',
    ],
    reflection:
      'From outside, the same sentence can sound like a break with ordinary care. Tajfel and Turner’s we/they cut is easier to see when you are not in the we. This toggle is a vantage, not a profile of anyone.',
  },
];

export const INTERNET_ACTIVITY: ChoiceActivityDef = {
  lead: 'Conway asked how, for whom, and compared with what. Gill and colleagues counted uses of the internet as a tool. Pick the claim those papers support. The internet is not a substitute for a cause.',
  reveal: 'lock',
  questions: [
    {
      id: 'net-claim',
      prompt: 'Which claim do Conway (2017) and Gill and colleagues (2017) support?',
      options: [
        {
          id: 'caused',
          label: 'The internet caused the violence in the cases they studied.',
          correct: false,
          explanation:
            'Neither paper treats the internet as a cause that replaces grievance, networks, or ideology. Gill counts uses of a tool. Conway wants harder comparison, not a slogan.',
        },
        {
          id: 'tool',
          label:
            'The internet is a tool that changes speed, reach, and opportunity. It does not replace older mechanisms, and it is not a sufficient cause.',
          correct: true,
          explanation:
            'That is the careful sentence. Conway refuses the existence question as enough. Gill quantifies behaviour. The internet changes how older mechanisms run. It does not retire them.',
        },
        {
          id: 'split',
          label:
            'Online radicalization is a clean category: people radicalize online or offline, not both.',
          correct: false,
          explanation:
            'Herath and Whittaker found mixed ties. Conway and Gill also refuse a clean split. Most studied paths are mixed.',
        },
      ],
    },
  ],
};

export const PAPER_LEAD =
  'Pick the card that states what the paper found. The other card is an overclaim the study cannot carry. Imageboards such as 4chan and 8chan appear in this literature as destinations. This page does not link to them.';

export const PAPER_ROUNDS: readonly PaperRound[] = [
  {
    id: 'ribeiro',
    paper: 'Ribeiro and colleagues, FAT* 2020',
    prompt: 'Which card states what the YouTube recommendation audit showed?',
    found: {
      id: 'ribeiro-found',
      label:
        'In that window, recommendation traces described pathways from milder political channels toward more extreme ones.',
      explanation:
        'An audit of what a ranker offered a crawler is a study of traces. It gave the pipeline story a method. It did not close the question.',
    },
    overclaim: {
      id: 'ribeiro-not',
      label:
        'The audit showed that a representative viewer later committed an act because of the ranker.',
      explanation:
        'The paper is not a study of what a representative person watched, and it is not a study of who later committed an act. Do not import a pathway into a person.',
    },
  },
  {
    id: 'later',
    paper: 'Chen, Nyhan, and colleagues, and Hosseinmardi and colleagues',
    prompt: 'Which card states what the later YouTube work showed?',
    found: {
      id: 'later-found',
      label:
        'Heavy consumption of extreme content was concentrated, and people often arrived via subscriptions or external links rather than a walk from mainstream videos.',
      explanation:
        'Later panel and consumption studies complicated the pipeline story. Arrival via search, a shared screenshot, a friend, or an off-platform link is common in that work.',
    },
    overclaim: {
      id: 'later-not',
      label:
        'Following the recommender was, on average, a walk from mainstream videos into extreme rooms in their windows, including onto 4chan and 8chan.',
      explanation:
        'Hosseinmardi’s programme and the Chen survey-behaviour pairing do not support that average walk, especially after platform changes around 2019. Naming 4chan or 8chan as destinations in the wider literature is not a ranker finding, and this page does not link there.',
    },
  },
];

export const COEFFICIENT_ACTIVITY: ChoiceActivityDef = {
  lead: 'Müller and Schwarz measured German anti-refugee Facebook activity beside local incidents. The method can travel. The coefficients cannot. The disciplined verb is temporally associated with, or coincides with.',
  reveal: 'lock',
  questions: [
    {
      id: 'import-coefficient',
      prompt:
        'Can you import the Müller and Schwarz coefficient into Amanah’s comment sample as a number about this collection?',
      options: [
        {
          id: 'yes',
          label: 'Yes',
          correct: false,
          explanation:
            'The coefficient belongs to that German Facebook sample, in that window, with those incident records. Amanah would be a different country, network, target, and counting rule. Importing the number is a category error.',
        },
        {
          id: 'no',
          label: 'No',
          correct: true,
          explanation:
            'Keep the pairing idea: a scoped speech series beside a reviewed incident list, with the window and coverage attached. Leave their estimate where it was measured. Two series that move together are temporally associated. They are not a general law.',
        },
      ],
    },
  ],
};

export const SCOPED_ACTIVITY: ChoiceActivityDef = {
  lead: 'A scoped record can count inside a window. It cannot count what it did not collect. Pick the sentence this tiny table can support. Open each sentence to see why it is allowed or not.',
  reveal: 'inspect',
  table: {
    caption:
      'Synthetic teaching table. Not Amanah data. A gap is missing collection, never a zero.',
    rows: [
      {
        id: 'week-one',
        window: '1 to 7 March',
        labelled: '12',
        collected: '400',
        coverage: 'collected',
        isGap: false,
      },
      {
        id: 'week-two',
        window: '8 to 14 March',
        labelled: 'gap',
        collected: 'gap',
        coverage: 'not collected',
        isGap: true,
      },
    ],
  },
  questions: [
    {
      id: 'scoped-sentence',
      prompt: 'Which sentence is this table allowed to support?',
      options: [
        {
          id: 'in-sample',
          label:
            'In this sample, 12 comments were classified as likely anti-Muslim hostility among 400 comments collected from 1 to 7 March.',
          correct: true,
          explanation:
            'The sentence keeps the numerator, the denominator, the window, and the label rule. It does not speak for a week that was not collected.',
        },
        {
          id: 'muslims-are',
          label: 'Muslims are more hated in March.',
          correct: false,
          explanation:
            'That is a claim about a people, not a count of labelled comments. A scoped record cannot promote a sample into a fact about Muslims.',
        },
        {
          id: 'zero-week',
          label: 'Hate dropped to zero in the second week.',
          correct: false,
          explanation:
            'The second week is a gap. Missing collection is not a quiet day. Drawing a gap as zero invents a drop the collectors never saw.',
        },
        {
          id: 'caused',
          label: 'This sample shows that the comments produced later incidents.',
          correct: false,
          explanation:
            'The table has no incident series, and a comment count is not a cause. Even a paired window would only support a temporal association, not this verb.',
        },
      ],
    },
  ],
};

export function getLessonActivityPage(moduleId: string): LessonActivityPage | undefined {
  return LESSON_ACTIVITY_PAGES.find((page) => page.moduleId === moduleId);
}

export function collectActivityText(): string {
  const parts: string[] = [
    SORT_LEAD,
    STAGE_LEAD,
    ROOM_LEAD,
    PAPER_LEAD,
    MECHANISM_ACTIVITY.lead,
    INTERNET_ACTIVITY.lead,
    COEFFICIENT_ACTIVITY.lead,
    SCOPED_ACTIVITY.lead,
  ];

  for (const item of SORT_ITEMS) {
    parts.push(item.statement, item.explanation);
  }
  for (const remark of STAGE_REMARKS) {
    parts.push(remark.remark, remark.explanation);
  }
  for (const vantage of ROOM_VANTAGES) {
    parts.push(vantage.label, vantage.reflection, ...vantage.cues);
  }
  for (const round of PAPER_ROUNDS) {
    parts.push(
      round.paper,
      round.prompt,
      round.found.label,
      round.found.explanation,
      round.overclaim.label,
      round.overclaim.explanation,
    );
  }
  for (const activity of [
    MECHANISM_ACTIVITY,
    INTERNET_ACTIVITY,
    COEFFICIENT_ACTIVITY,
    SCOPED_ACTIVITY,
  ]) {
    for (const question of activity.questions) {
      parts.push(question.prompt);
      for (const option of question.options) {
        parts.push(option.label, option.explanation);
      }
    }
  }

  return parts.join(' ');
}
