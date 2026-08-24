import { InfoTip } from '@/components/ui/InfoTip';
import { usePageTitle } from '@/hooks/usePageTitle';

import { PlatformReportDraft } from './PlatformReportDraft';
import { PolicyReportFlow } from './PolicyReportFlow';
import { ResearchReportPanel } from './ResearchReportPanel';
import { REPORT_SECTIONS } from './mock';

import styles from './ReportsPage.module.css';

/**
 * Reports: the F-S14 platform-report draft first, then the F-S16 research
 * snapshot, which now creates and reads real immutable snapshots through
 * `/v1/research-reports`. Review never hosts this form.
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

      <section className={styles.card} aria-labelledby="preview-heading">
        <div className={styles.headingRow}>
          <h2 id="preview-heading" className={styles.sectionHeading}>
            What the report contains
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
    </div>
  );
}
