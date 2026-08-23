/**
 * Marketing page sections. Hrefs include the home path so they still reach
 * the right block when the header or footer is shown on /resources or /login.
 */
export const MARKETING_SECTIONS = [
  { href: '/#the-problem', label: 'Problem' },
  { href: '/#the-path', label: 'Radicalization' },
  { href: '/#why-it-matters', label: 'Why' },
  { href: '/#our-philosophy', label: 'Philosophy' },
  { href: '/#what-it-does', label: 'Product' },
  { href: '/#how-it-works', label: 'How' },
  { href: '/#responsible-use', label: 'Responsible' },
  { href: '/#methodology', label: 'Method' },
] as const;
