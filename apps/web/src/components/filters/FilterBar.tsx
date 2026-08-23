import { useCallback } from 'react';

import type { AppliedFilters, FilterOption, FilterOptions } from '@/api';
import { InfoTip } from '@/components/ui/InfoTip';
import { FILTER_PARAMS } from '@/features/dashboard/useDashboardFilters';

import { DateRangePicker } from './DateRangePicker';

import styles from './FilterBar.module.css';

interface FilterBarProps {
  options: FilterOptions;
  applied: AppliedFilters;
  onRangeChange: (from: string, to: string) => void;
  onToggle: (param: string, value: string) => void;
  onClear: () => void;
  activeCount: number;
}

interface ChipGroupProps {
  legend: string;
  hint: string;
  param: string;
  options: readonly FilterOption[];
  selected: readonly string[];
  onToggle: (param: string, value: string) => void;
}

/**
 * The scope controls for every figure below them.
 *
 * Two kinds of filter live here and the difference matters. Dates and platforms
 * change what was looked at, so they change denominators. Type, severity and
 * review state select among the classifications already made, so they change the
 * numerator and leave the denominator alone. The group hints say which is which,
 * because a reader who mistakes one for the other will misread every rate on the
 * page.
 */
export function FilterBar({
  options,
  applied,
  onRangeChange,
  onToggle,
  onClear,
  activeCount,
}: FilterBarProps) {
  return (
    <section className={styles.bar} aria-labelledby="filters-heading">
      <div className={styles.head}>
        <div className={styles.headingRow}>
          <h2 id="filters-heading" className={styles.heading}>
            Filters
          </h2>
          <InfoTip label="Filters">
            Dates and sources change what was collected, so they change denominators. Type,
            severity, and review state select among classifications already made, so they change the
            numerator only.
          </InfoTip>
        </div>
        <p className={styles.scope}>
          Showing {applied.from} to {applied.to}
          {applied.platforms.length === 0
            ? ', every monitored source'
            : `, ${applied.platforms.length} of ${String(options.platforms.length)} sources`}
          .
        </p>
        {activeCount > 0 && (
          <button type="button" className={styles.clear} onClick={onClear}>
            Clear {activeCount} filter{activeCount === 1 ? '' : 's'}
          </button>
        )}
      </div>

      <div className={styles.row}>
        <DateRangePicker
          from={applied.from}
          to={applied.to}
          availableFrom={options.available.from}
          availableTo={options.available.to}
          onChange={onRangeChange}
        />

        <ChipGroup
          legend="Source"
          hint="Changes what was collected, so it changes the denominators."
          param={FILTER_PARAMS.platform}
          options={options.platforms}
          selected={applied.platforms}
          onToggle={onToggle}
        />
      </div>

      <div className={styles.row}>
        <ChipGroup
          legend="Type of harm"
          hint="Selects among classifications already made. The denominator stays the same."
          param={FILTER_PARAMS.hateType}
          options={options.hateTypes}
          selected={applied.hateTypes}
          onToggle={onToggle}
        />
        <ChipGroup
          legend="Severity"
          hint="Model judgement, 0 borderline to 3 severe."
          param={FILTER_PARAMS.severity}
          options={options.severityBands}
          selected={applied.severityBands}
          onToggle={onToggle}
        />
        <ChipGroup
          legend="Review state"
          hint="How far a classification has travelled through human review."
          param={FILTER_PARAMS.reviewState}
          options={options.reviewStates}
          selected={applied.reviewStates}
          onToggle={onToggle}
        />
      </div>
    </section>
  );
}

function ChipGroup({ legend, hint, param, options, selected, onToggle }: ChipGroupProps) {
  return (
    <fieldset className={styles.group}>
      <legend className={styles.legend}>{legend}</legend>
      <p className={styles.hint}>{hint}</p>
      <div className={styles.chips}>
        {options.map((option) => (
          <Chip
            key={option.value}
            param={param}
            option={option}
            isSelected={selected.includes(option.value)}
            onToggle={onToggle}
          />
        ))}
      </div>
    </fieldset>
  );
}

interface ChipProps {
  param: string;
  option: FilterOption;
  isSelected: boolean;
  onToggle: (param: string, value: string) => void;
}

function Chip({ param, option, isSelected, onToggle }: ChipProps) {
  const handleClick = useCallback((): void => {
    onToggle(param, option.value);
  }, [onToggle, option.value, param]);

  return (
    <button
      type="button"
      className={isSelected ? `${styles.chip} ${styles.chipOn}` : styles.chip}
      onClick={handleClick}
      aria-pressed={isSelected}
    >
      {option.label}
      {option.count !== null && (
        <span className={styles.chipCount}>{option.count.toLocaleString('en-GB')}</span>
      )}
    </button>
  );
}
