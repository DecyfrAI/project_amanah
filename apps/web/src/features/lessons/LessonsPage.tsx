import { useCallback, useMemo, useState, type ChangeEvent } from 'react';
import { Link } from 'react-router-dom';

import { MindsetStages } from '@/components/marketing/MindsetStages';
import { usePageTitle } from '@/hooks/usePageTitle';

import {
  CATEGORY_LABELS,
  externalLinkProps,
  filterResources,
  isResourceCategoryFilter,
  isResourceScopeFilter,
  LESSON_CASES,
  LESSON_MODULES,
  LESSON_RESOURCES,
  lessonReaderPath,
  RESOURCE_CATEGORIES,
  RESOURCE_SCOPES,
  SCOPE_LABELS,
  type LessonModule,
  type LessonResource,
  type ResourceCategoryFilter,
  type ResourceScopeFilter,
} from './lesson-copy';

import styles from './LessonsPage.module.css';

interface LessonsPageProps {
  /** Extra page padding when the marketing header is fixed above this view. */
  framedForMarketing?: boolean;
}

/**
 * Syllabus catalog plus the spec 9.12 resource list (F-S15).
 *
 * Eight numbered modules stay first. External desks and crisis lines sit
 * below, behind Category and Place dropdowns. The reader is a separate route.
 */
export function LessonsPage({ framedForMarketing = false }: LessonsPageProps) {
  usePageTitle('Lessons');
  const catalogClass = framedForMarketing ? `${styles.page} ${styles.pagePublic}` : styles.page;
  const [category, setCategory] = useState<ResourceCategoryFilter>('all');
  const [scope, setScope] = useState<ResourceScopeFilter>('all');
  const resources = useMemo(
    () => filterResources(LESSON_RESOURCES, category, scope),
    [category, scope],
  );

  const handleCategoryChange = useCallback((event: ChangeEvent<HTMLSelectElement>): void => {
    const next = event.currentTarget.value;
    if (isResourceCategoryFilter(next)) {
      setCategory(next);
    }
  }, []);

  const handleScopeChange = useCallback((event: ChangeEvent<HTMLSelectElement>): void => {
    const next = event.currentTarget.value;
    if (isResourceScopeFilter(next)) {
      setScope(next);
    }
  }, []);

  return (
    <div className={catalogClass}>
      <header className={styles.header}>
        <h1 className={styles.title}>Lessons</h1>
        <p className={styles.lead}>
          Eight short modules on how radicalization is studied, then public case studies of
          documented paths through online rooms. Each module is published research. Each case is an
          official record or contemporary reporting. The cases are here so the impact of those rooms
          is concrete, and so prevention and monitoring have names and dates to work from.
        </p>
      </header>

      <ul className={styles.moduleList}>
        {LESSON_MODULES.map((module) => (
          <li key={module.id}>
            <ModuleCard module={module} publicRoute={framedForMarketing} />
          </li>
        ))}
      </ul>

      <section className={styles.caseSection} aria-labelledby="case-studies-heading">
        <h2 id="case-studies-heading" className={styles.sectionHeading}>
          Public case studies
        </h2>
        <p className={styles.modelLead}>
          Incel forums, imageboards, livestreams, Gab, Discord, and ordinary social posts sit on
          documented paths that later ended in public violence, including attacks on mosques and
          other houses of worship. The stills are generated. They are not photographs of the attacks
          or of anyone involved. A timeline is not proof that one post produced the violence. The
          rooms are still the place the record named.
        </p>
        <ul className={styles.moduleList}>
          {LESSON_CASES.map((entry) => (
            <li key={entry.id}>
              <CaseCard entry={entry} publicRoute={framedForMarketing} />
            </li>
          ))}
        </ul>
      </section>

      <section className={styles.modelSection} aria-labelledby="mindset-model-heading">
        <h2 id="mindset-model-heading" className={styles.sectionHeading}>
          How a grievance is retargeted
        </h2>
        <p className={styles.modelLead}>
          Randy Borum’s 2003 sketch, the same four-stage figure as on the marketing site. It is a
          published heuristic, not an Amanah finding and not a staircase every poster climbs. Module
          03 walks it with an exercise.
        </p>
        <MindsetStages labelledBy="mindset-model-heading" />
      </section>

      <section className={styles.resourceSection} aria-labelledby="resources-heading">
        <h2 id="resources-heading" className={styles.sectionHeading}>
          Resources
        </h2>
        <p className={styles.resourceLead}>
          External desks and lines, including crisis help. They are not Amanah findings, and they
          are not the syllabus. If you are in immediate danger, contact local emergency services.
        </p>

        <div className={styles.filters}>
          <FilterSelect
            id="lesson-category"
            label="Category"
            value={category}
            options={RESOURCE_CATEGORIES}
            labels={CATEGORY_LABELS}
            onChange={handleCategoryChange}
          />
          <FilterSelect
            id="lesson-place"
            label="Place"
            value={scope}
            options={RESOURCE_SCOPES}
            labels={SCOPE_LABELS}
            onChange={handleScopeChange}
          />
        </div>

        {resources.length === 0 ? (
          <output className={styles.empty}>
            No reviewed resource matches that category and place. Choose Every category or Every
            place, or clear one of the filters.
          </output>
        ) : (
          <ul className={styles.resourceList}>
            {resources.map((resource) => (
              <li key={resource.id}>
                <ResourceCard resource={resource} />
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function ModuleCard({ module, publicRoute }: { module: LessonModule; publicRoute: boolean }) {
  const sourceLabel = module.sources.length === 1 ? '1 source' : `${module.sources.length} sources`;

  return (
    <article className={styles.card} aria-labelledby={`${module.id}-title`}>
      <Link className={styles.cardLink} to={lessonReaderPath(module.id, publicRoute)}>
        <p className={styles.number}>{module.number}</p>
        <h2 id={`${module.id}-title`} className={styles.cardTitle}>
          {module.title}
        </h2>
        <p className={styles.thesis}>{module.thesis}</p>
        <p className={styles.meta}>
          {module.minutes} min · {sourceLabel}
        </p>
      </Link>
    </article>
  );
}

function CaseCard({ entry, publicRoute }: { entry: LessonModule; publicRoute: boolean }) {
  const sourceLabel = entry.sources.length === 1 ? '1 source' : `${entry.sources.length} sources`;
  const place = entry.place ?? 'Public record';
  const dateLabel = entry.dateLabel ?? '';

  return (
    <article className={styles.card} aria-labelledby={`${entry.id}-title`}>
      <Link className={styles.cardLink} to={lessonReaderPath(entry.id, publicRoute)}>
        {entry.hero !== undefined ? (
          <img className={styles.caseImage} src={entry.hero.src} alt={entry.hero.alt} />
        ) : null}
        <p className={styles.number}>
          {place}
          {dateLabel.length > 0 ? ` · ${dateLabel}` : ''}
        </p>
        <h2 id={`${entry.id}-title`} className={styles.cardTitle}>
          {entry.title}
        </h2>
        <p className={styles.thesis}>{entry.thesis}</p>
        <p className={styles.meta}>
          {entry.minutes} min · {sourceLabel}
        </p>
      </Link>
    </article>
  );
}

function ResourceCard({ resource }: { resource: LessonResource }) {
  return (
    <article className={styles.resourceCard} aria-labelledby={`${resource.id}-title`}>
      <p className={styles.kicker}>
        {CATEGORY_LABELS[resource.category]} · {SCOPE_LABELS[resource.scope]}
      </p>
      <h3 id={`${resource.id}-title`} className={styles.resourceTitle}>
        {resource.title}
      </h3>
      <p className={styles.organization}>{resource.organization}</p>
      <p className={styles.resourceSummary}>{resource.summary}</p>
      <p className={styles.resourceMeta}>
        Last reviewed {resource.lastReviewed} by {resource.reviewer}
      </p>
      <a className={styles.resourceLink} href={resource.href} {...externalLinkProps(resource.href)}>
        {resource.title} (opens in a new tab)
      </a>
    </article>
  );
}

interface FilterSelectProps<T extends string> {
  id: string;
  label: string;
  value: T;
  options: readonly T[];
  labels: Record<T, string>;
  onChange: (event: ChangeEvent<HTMLSelectElement>) => void;
}

function FilterSelect<T extends string>({
  id,
  label,
  value,
  options,
  labels,
  onChange,
}: FilterSelectProps<T>) {
  return (
    <div className={styles.filterField}>
      <label className={styles.filterLabel} htmlFor={id}>
        {label}
      </label>
      <select className={styles.filterControl} id={id} name={id} value={value} onChange={onChange}>
        {options.map((option) => (
          <option key={option} value={option}>
            {labels[option]}
          </option>
        ))}
      </select>
    </div>
  );
}
