import { isReportPlatform, PLATFORM_REPORT_CATALOG } from './prepare-report-draft';

import styles from './PlatformReportPaths.module.css';

interface PlatformReportPathsProps {
  readonly platform: string;
}

/**
 * Official policy and report pages for the selected platform.
 *
 * Shown before Generate so a person can report in-product. Amanah never
 * submits those forms, and the draft To field stays a fixture placeholder.
 */
export function PlatformReportPaths({ platform }: PlatformReportPathsProps) {
  if (!isReportPlatform(platform)) {
    return null;
  }

  const catalog = PLATFORM_REPORT_CATALOG[platform];
  const headingId = `platform-paths-${catalog.id}`;

  if (catalog.policyUrl === null && catalog.officialReportUrl === null) {
    return (
      <aside className={styles.paths} aria-labelledby={headingId}>
        <h3 className={styles.heading} id={headingId}>
          Official reporting
        </h3>
        <p className={styles.copy}>
          Look up that platform&apos;s own report page. Amanah does not keep a public mailbox for
          every host, and it will not submit a report for you.
        </p>
      </aside>
    );
  }

  return (
    <aside className={styles.paths} aria-labelledby={headingId}>
      <h3 className={styles.heading} id={headingId}>
        Official {catalog.label} reporting
      </h3>
      <p className={styles.copy}>{catalog.toNote}</p>
      <ul className={styles.list}>
        {catalog.policyUrl !== null && catalog.policyLabel !== null && (
          <li>
            <a
              className={styles.link}
              href={catalog.policyUrl}
              rel="noopener noreferrer"
              target="_blank"
            >
              {catalog.policyLabel} (opens in a new tab)
            </a>
          </li>
        )}
        {catalog.officialReportUrl !== null && catalog.officialReportLabel !== null && (
          <li>
            <a
              className={styles.link}
              href={catalog.officialReportUrl}
              rel="noopener noreferrer"
              target="_blank"
            >
              {catalog.officialReportLabel} (opens in a new tab)
            </a>
          </li>
        )}
      </ul>
    </aside>
  );
}
