import { InfoTip } from '@/components/ui/InfoTip';
import { MockupNotice } from '@/components/ui/MockupNotice';
import { StatusPill } from '@/components/ui/StatusPill';
import { usePageTitle } from '@/hooks/usePageTitle';

import { CONNECTORS, DATAPACK, type Connector } from './mock';

import styles from './ConnectionsPage.module.css';

/**
 * Connections, laid out from local constants for design review.
 *
 * The value of this page is that it admits what is not running, since a gap in
 * collection is the most common reason a chart looks calmer than reality. So a
 * connector with no data shows the reason instead of a zero, and every status
 * carries a word and a glyph rather than a colour a reader has to learn.
 */
export function ConnectionsPage() {
  usePageTitle('Connections');

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Connections</h1>
        <p className={styles.lead}>
          Integration health, told plainly. Every source here uses a documented API or a permitted
          feed. There is no scraping fallback anywhere in this list, and no credential is displayed
          on this page or held in the browser.
        </p>
      </header>

      <MockupNotice detail="The five connectors, their run times, and their counts are illustrations of connector states, not readings from a collector." />

      <section className={styles.connectors} aria-labelledby="connectors-heading">
        <div className={styles.headingRow}>
          <h2 id="connectors-heading" className={styles.sectionHeading}>
            Sources
          </h2>
          <InfoTip label="Sources">
            Every source uses a documented API or a permitted feed. A connector with no data shows
            the reason instead of a zero.
          </InfoTip>
        </div>
        <ul className={styles.connectorList}>
          {CONNECTORS.map((connector) => (
            <ConnectorCard key={connector.id} connector={connector} />
          ))}
        </ul>
      </section>

      <section className={styles.card} aria-labelledby="provenance-heading">
        <div className={styles.headingRow}>
          <h2 id="provenance-heading" className={styles.sectionHeading}>
            Open datapack provenance
          </h2>
          <InfoTip label="Open datapack provenance">
            Nothing from a datapack appears until its licence, manifest, and file hash have been
            reviewed.
          </InfoTip>
        </div>
        <p className={styles.provenanceLead}>
          Nothing from a datapack appears on screen until its licence has been reviewed, its
          manifest approved, and its file hash verified against the file that was actually imported.
        </p>
        <dl className={styles.provenanceFacts}>
          <div className={styles.fact}>
            <dt className={styles.term}>Dataset</dt>
            <dd className={styles.value}>{DATAPACK.datasetName}</dd>
          </div>
          <div className={styles.fact}>
            <dt className={styles.term}>Provider</dt>
            <dd className={styles.value}>{DATAPACK.provider}</dd>
          </div>
          <div className={styles.fact}>
            <dt className={styles.term}>Version</dt>
            <dd className={styles.value}>{DATAPACK.version}</dd>
          </div>
          <div className={styles.fact}>
            <dt className={styles.term}>Licence</dt>
            <dd className={styles.value}>
              <a className={styles.link} href={DATAPACK.licenceUrl}>
                {DATAPACK.licence}
              </a>
            </dd>
          </div>
          <div className={styles.fact}>
            <dt className={styles.term}>Retrieved</dt>
            <dd className={styles.value}>{DATAPACK.retrievedAt}</dd>
          </div>
          <div className={styles.fact}>
            <dt className={styles.term}>Rows imported</dt>
            <dd className={styles.value}>
              {DATAPACK.rowsImported.toLocaleString('en')} of{' '}
              {DATAPACK.rowCount.toLocaleString('en')} rows in the file
            </dd>
          </div>
          <div className={styles.factWide}>
            <dt className={styles.term}>File hash, SHA-256</dt>
            <dd className={styles.hash}>{DATAPACK.fileHash}</dd>
          </div>
          <div className={styles.factWide}>
            <dt className={styles.term}>Approval</dt>
            <dd className={styles.value}>{DATAPACK.approvedBy}</dd>
          </div>
        </dl>
        <p className={styles.annotationNote}>{DATAPACK.annotationNote}</p>
      </section>
    </div>
  );
}

interface ConnectorCardProps {
  connector: Connector;
}

function ConnectorCard({ connector }: ConnectorCardProps) {
  const headingId = `${connector.id}-name`;
  const coverage =
    connector.daysCollected === null
      ? 'No days collected'
      : `${connector.daysCollected} of the last 7 days collected`;
  const items =
    connector.itemsLastWeek === null
      ? 'Gap, not zero'
      : `${connector.itemsLastWeek.toLocaleString('en')} items`;

  return (
    <li className={styles.connector}>
      <article aria-labelledby={headingId}>
        <div className={styles.connectorTop}>
          <h3 id={headingId} className={styles.connectorName}>
            {connector.name}
          </h3>
          <StatusPill indicator={connector.indicator} label={connector.statusLabel} />
        </div>

        <dl className={styles.connectorFacts}>
          <div className={styles.fact}>
            <dt className={styles.term}>Collects</dt>
            <dd className={styles.value}>{connector.collects}</dd>
          </div>
          <div className={styles.fact}>
            <dt className={styles.term}>Authorisation</dt>
            <dd className={styles.value}>{connector.authorisation}</dd>
          </div>
          <div className={styles.fact}>
            <dt className={styles.term}>Last successful run</dt>
            <dd className={styles.value}>
              {connector.lastSuccessfulRun ?? 'No successful run recorded'}
            </dd>
          </div>
          <div className={styles.fact}>
            <dt className={styles.term}>Last 7 days</dt>
            <dd className={styles.value}>
              {coverage}, {items}
              {connector.gapReason !== null && (
                <span className={styles.gapReason}>{connector.gapReason}</span>
              )}
            </dd>
          </div>
        </dl>

        <p className={styles.caveat}>{connector.caveat}</p>
      </article>
    </li>
  );
}
