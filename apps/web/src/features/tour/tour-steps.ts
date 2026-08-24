export interface TourStep {
  readonly id: string;
  readonly title: string;
  readonly body: string;
  /** Workspace route to show under the card for this step. */
  readonly to: string;
}

/**
 * Tab-by-tab guide, in the same order as the sidebar.
 *
 * Chrome is introduced once on Overview. Later steps stay on their tab and do
 * not jump back to an earlier destination.
 */
export const TOUR_STEPS: readonly TourStep[] = [
  {
    id: 'workspace',
    title: 'The workspace',
    to: '/app',
    body: 'The left rail is every tab, in this order: Overview, Explorer, Insights, Lessons, Review, Reports, Contributions, Connections, then Settings. Collapse it to icons when you need width. Theme and your name sit at the foot of the rail. Signed-in identity and Log out live in the top bar. The Tour control and Ask Amanah sit in the bottom-right. You can replay this walk from Tour or from Settings.',
  },
  {
    id: 'overview',
    title: 'Overview',
    to: '/app',
    body: 'This is the main reading. Coverage at the top names the window, the sources, and any collection gap. Key figures each carry a numerator and a denominator. The question mark states the definition. Over time toggles rate and volume. Composition breaks likely-hate items by type, severity, source, and review state. In the news sits beside the window as context, not as a classification. Click a figure, a day, a bar, or a slice to open Explorer on that same filter.',
  },
  {
    id: 'explorer',
    title: 'Explorer',
    to: '/app/explorer',
    body: 'The table of reviewed examples behind the figures. Filters from Overview carry over, so a drill-down lands on the same slice. Each row shows the comment wording, the source, the model label, and the review state. A pending row is a proposal, not a finding. There is no author search and no person ranking.',
  },
  {
    id: 'insights',
    title: 'Insights',
    to: '/app/insights',
    body: 'Snapshots you start from a day, a key figure, or a composition row. Each card keeps the counts it rests on. Open a card to read the finding and the discussion beside it. Notes attach to that snapshot. They do not rewrite the stored numbers. This is a research thread, not a public forum.',
  },
  {
    id: 'lessons',
    title: 'Lessons',
    to: '/app/lessons',
    body: 'Eight short research modules on how radicalization is studied, then public case studies of documented paths through online rooms, then a resource list with crisis lines. Case studies name official records and news reporting. They are for education. Marketing no longer opens this catalog before you sign in.',
  },
  {
    id: 'review',
    title: 'Review',
    to: '/app/review',
    body: 'Items the pipeline could not settle alone. A decision appends beside the model prediction and never overwrites it. Comment wording is shown in full. Prepare a report sends you to Reports with the item referenced. Queue figures on this tab are still a layout mock.',
  },
  {
    id: 'reports',
    title: 'Reports',
    to: '/app/reports',
    body: 'Prepare a platform report for a person to send. Upload a screenshot or describe what you saw, choose the platform, and generate a draft. You copy, download, or open it in mail. Amanah never submits the report. Research-export controls below the draft are still illustrations.',
  },
  {
    id: 'contributions',
    title: 'Contributions',
    to: '/app/contributions',
    body: 'Everything you submitted, disputed, or prepared, in one owner-scoped history. Only you can read your own rows. A prepared report shows as prepared until you record that you filed it yourself: Amanah never submits one, so no status here is a platform acknowledgement.',
  },
  {
    id: 'connections',
    title: 'Connections',
    to: '/app/connections',
    body: 'Collector status and collection gaps by source. A failed run is a gap, never a zero count. Use this tab to see whether a quiet figure is a quiet day or a missed collection. Connector cards here are illustrations of those states.',
  },
  {
    id: 'settings',
    title: 'Settings',
    to: '/app/settings',
    body: 'Theme (also on the rail), table density, and Replay workspace tour. Content-safety and density controls on this page apply in this tab until a preferences endpoint exists.',
  },
  {
    id: 'profile',
    title: 'Profile',
    to: '/app/profile',
    body: 'Display name, avatar, and the notes you have left. Open this from the rail footer or the top bar. Nothing here is a ranking of people, and person-level search is out of scope.',
  },
];
