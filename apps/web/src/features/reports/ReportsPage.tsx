import { InfoTip } from '@/components/ui/InfoTip';
import { MockupNotice } from '@/components/ui/MockupNotice';
import { StatusPill } from '@/components/ui/StatusPill';
import { usePageTitle } from '@/hooks/usePageTitle';

import { PlatformReportDraft } from './PlatformReportDraft';
import {
  REPORT_SECTIONS,
  REPORT_SNAPSHOTS,
  SCOPE_DATE_RANGE,
  SCOPE_FIELDS,
  type ScopeField,
} from './mock';

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

      <MockupNotice
        detail="The scope controls and snapshots below describe research reports that were never prepared."
        controlsNote="Those research-report controls are inert. Preparing a platform report, above, writes a draft for you to copy or download. It does not send anything."
      />

      <div className={styles.columns}>
        <section className={styles.card} aria-labelledby="scope-heading">
          <div className={styles.headingRow}>
            <h2 id="scope-heading" className={styles.sectionHeading}>
              Report scope
            </h2>
            <InfoTip label="Report scope">
              The filters this report would freeze. A report describes the monitored sample it
              names, never a whole platform.
            </InfoTip>
          </div>
          <form className={styles.form}>
            <fieldset className={styles.fieldset} disabled aria-describedby="scope-unavailable">
              <legend className={styles.legend}>Filters this report would freeze</legend>

              <div className={styles.dateRow}>
                <div className={styles.field}>
                  <label className={styles.label} htmlFor="date-from">
                    Window starts
                  </label>
                  <input
                    className={styles.control}
                    id="date-from"
                    name="date-from"
                    type="date"
                    defaultValue={SCOPE_DATE_RANGE.from}
                  />
                </div>
                <div className={styles.field}>
                  <label className={styles.label} htmlFor="date-to">
                    Window ends
                  </label>
                  <input
                    className={styles.control}
                    id="date-to"
                    name="date-to"
                    type="date"
                    defaultValue={SCOPE_DATE_RANGE.to}
                  />
                </div>
              </div>

              {SCOPE_FIELDS.map((field) => (
                <ScopeSelect key={field.id} field={field} />
              ))}
            </fieldset>

            <p id="scope-unavailable" className={styles.unavailable}>
              These controls are disabled because report generation needs the research-report API,
              which is not connected yet. The values shown are the defaults the finished form will
              open with.
            </p>

            <button
              type="button"
              className={styles.primaryAction}
              disabled
              aria-describedby="scope-unavailable"
            >
              Generate report
            </button>
          </form>
        </section>

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
      </div>

      <section className={styles.card} aria-labelledby="export-heading">
        <div className={styles.headingRow}>
          <h2 id="export-heading" className={styles.sectionHeading}>
            Export
          </h2>
          <InfoTip label="Export">
            Aggregate CSV carries counts and denominators only. Item-level export needs elevated
            permission and is not part of this view.
          </InfoTip>
        </div>
        <p className={styles.exportNote} id="export-unavailable">
          CSV export carries aggregate data only: the counts and denominators the charts showed, and
          nothing else. Item-level export needs elevated permission and is not part of this view.
          Both are unavailable here, because there is no report to download and no export endpoint
          to ask.
        </p>
        <div className={styles.exportActions}>
          <button
            type="button"
            className={styles.action}
            disabled
            aria-describedby="export-unavailable"
          >
            Download aggregate CSV
          </button>
          <button
            type="button"
            className={styles.action}
            disabled
            aria-describedby="export-unavailable"
          >
            Print or save as PDF
          </button>
        </div>
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

interface ScopeSelectProps {
  field: ScopeField;
}

function ScopeSelect({ field }: ScopeSelectProps) {
  return (
    <div className={styles.field}>
      <label className={styles.label} htmlFor={field.id}>
        {field.label}
      </label>
      <select className={styles.control} id={field.id} name={field.id} defaultValue={field.value}>
        {field.options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </div>
  );
}
