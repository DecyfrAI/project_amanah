import { InfoTip } from '@/components/ui/InfoTip';
import { MockupNotice } from '@/components/ui/MockupNotice';
import { StatusPill } from '@/components/ui/StatusPill';
import { usePageTitle } from '@/hooks/usePageTitle';

import { PlatformReportDraft } from './PlatformReportDraft';
import { PolicyReportFlow } from './PolicyReportFlow';
import { ResearchReportPanel } from './ResearchReportPanel';
import { REPORT_SECTIONS, REPORT_SNAPSHOTS } from './mock';

import styles from './ReportsPage.module.css';

/**
 * Reports: F-S14 platform-report drafts first, then the F-S16 research-export
 * mock. Review never hosts this form.
 */
export function ReportsPage() {
  usePageTitle('Reports');

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Reports</h1>
        <p className={styles.lead}>
          Prepare a platform report for a person to send, or freeze a research export that states
          its own scope. Amanah never submits a report to a platform.
        </p>
      </header>

      <PlatformReportDraft />

      <PolicyReportFlow />

      <ResearchReportPanel />

      <MockupNotice detail="The snapshots listed at the end of this page describe research reports that were never prepared." />

      <section className={styles.card} aria-labelledby="preview-heading">
        <div className={styles.headingRow}>
          <h2 id="preview-heading" className={styles.sectionHeading}>
            What the report will contain
          </h2>
          <InfoTip label="Report contents">
            Coverage and limitations travel with the figures. A number without its denominator is
            the failure this layout exists to prevent.
          </InfoTip>
        </div>
        <p className={styles.previewLead}>
          Nine sections, in this order. Coverage and limitations are not appendices: a figure that
          travels without its denominator is the failure this layout exists to prevent.
        </p>
        <ol className={styles.sectionList}>
          {REPORT_SECTIONS.map((section) => (
            <li key={section.id} className={styles.sectionItem}>
              <p className={styles.sectionName}>{section.name}</p>
              <p className={styles.sectionDetail}>{section.detail}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className={styles.snapshots} aria-labelledby="snapshots-heading">
        <div className={styles.headingRow}>
          <h2 id="snapshots-heading" className={styles.sectionHeading}>
            Previously prepared snapshots
          </h2>
          <InfoTip label="Prepared snapshots">
            Frozen claims about a bounded sample. These rows are illustrations of reports that were
            never prepared.
          </InfoTip>
        </div>
        <ul className={styles.snapshotList}>
          {REPORT_SNAPSHOTS.map((snapshot) => (
            <li key={snapshot.id} className={styles.snapshot}>
              <div className={styles.snapshotTop}>
                <h3 className={styles.snapshotTitle}>{snapshot.title}</h3>
                <StatusPill indicator={snapshot.indicator} label={snapshot.statusLabel} />
              </div>
              <dl className={styles.snapshotFacts}>
                <div className={styles.snapshotFact}>
                  <dt className={styles.term}>Window</dt>
                  <dd className={styles.value}>{snapshot.window}</dd>
                </div>
                <div className={styles.snapshotFact}>
                  <dt className={styles.term}>Filters applied</dt>
                  <dd className={styles.value}>{snapshot.filters}</dd>
                </div>
                <div className={styles.snapshotFact}>
                  <dt className={styles.term}>Created</dt>
                  <dd className={styles.value}>{snapshot.createdAt}</dd>
                </div>
                <div className={styles.snapshotFact}>
                  <dt className={styles.term}>Reference</dt>
                  <dd className={styles.value}>{snapshot.id}</dd>
                </div>
              </dl>
              <p className={styles.snapshotCaveat}>{snapshot.caveat}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
