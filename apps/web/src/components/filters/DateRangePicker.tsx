import { useCallback, useMemo, useRef, useState } from 'react';

import styles from './DateRangePicker.module.css';

interface DateRangePickerProps {
  from: string;
  to: string;
  /** First and last day with collection behind it. Outside this, there is no data. */
  availableFrom: string;
  availableTo: string;
  onChange: (from: string, to: string) => void;
}

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const;

const PRESETS = [
  { label: 'Last 7 days', days: 7 },
  { label: 'Last 14 days', days: 14 },
  { label: 'Last 30 days', days: 30 },
] as const;

function toIso(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function fromIso(value: string): Date {
  return new Date(`${value}T00:00:00Z`);
}

function addDays(value: string, days: number): string {
  const date = fromIso(value);
  date.setUTCDate(date.getUTCDate() + days);
  return toIso(date);
}

function startOfMonth(value: string): string {
  return `${value.slice(0, 7)}-01`;
}

function shiftMonth(monthStart: string, months: number): string {
  const date = fromIso(monthStart);
  date.setUTCMonth(date.getUTCMonth() + months);
  return toIso(date);
}

function monthLabel(monthStart: string): string {
  return fromIso(monthStart).toLocaleDateString('en-GB', {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  });
}

function dayLabel(iso: string): string {
  return fromIso(iso).toLocaleDateString('en-GB', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  });
}

/** Cells for one month grid, with leading blanks so weekdays line up. */
function monthCells(monthStart: string): (string | null)[] {
  const first = fromIso(monthStart);
  const daysInMonth = new Date(
    Date.UTC(first.getUTCFullYear(), first.getUTCMonth() + 1, 0),
  ).getUTCDate();

  // getUTCDay is Sunday-first; the grid is Monday-first.
  const leading = (first.getUTCDay() + 6) % 7;
  const cells: (string | null)[] = Array.from({ length: leading }, () => null);
  for (let day = 1; day <= daysInMonth; day += 1) {
    cells.push(`${monthStart.slice(0, 7)}-${String(day).padStart(2, '0')}`);
  }
  return cells;
}

/**
 * A two-step date range picker over the days that actually have collection.
 *
 * The first click sets the start and the second sets the end, which is fewer
 * controls than two separate calendars and matches how people describe a window
 * out loud. Days outside the collected range are disabled rather than hidden, so
 * the reader can see where the record begins and ends instead of inferring it.
 *
 * Every day is a real button in a grid, so the whole calendar is reachable by
 * keyboard with no custom key handling, and each one carries its full date as its
 * accessible name rather than a bare number.
 */
export function DateRangePicker({
  from,
  to,
  availableFrom,
  availableTo,
  onChange,
}: DateRangePickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [monthStart, setMonthStart] = useState(() => startOfMonth(to));
  const [pendingStart, setPendingStart] = useState<string | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  const months = useMemo(() => [monthStart, shiftMonth(monthStart, 1)], [monthStart]);

  const toggleOpen = useCallback((): void => {
    setIsOpen((open) => !open);
    setPendingStart(null);
  }, []);

  const goBack = useCallback((): void => {
    setMonthStart((current) => shiftMonth(current, -1));
  }, []);

  const goForward = useCallback((): void => {
    setMonthStart((current) => shiftMonth(current, 1));
  }, []);

  const handleDayClick = useCallback(
    (day: string): void => {
      if (pendingStart === null) {
        setPendingStart(day);
        return;
      }
      const [start, end] = pendingStart <= day ? [pendingStart, day] : [day, pendingStart];
      setPendingStart(null);
      setIsOpen(false);
      triggerRef.current?.focus();
      onChange(start, end);
    },
    [onChange, pendingStart],
  );

  const applyPreset = useCallback(
    (days: number): void => {
      const start = addDays(availableTo, -(days - 1));
      onChange(start < availableFrom ? availableFrom : start, availableTo);
      setIsOpen(false);
      triggerRef.current?.focus();
    },
    [availableFrom, availableTo, onChange],
  );

  const applyFullRange = useCallback((): void => {
    onChange(availableFrom, availableTo);
    setIsOpen(false);
    triggerRef.current?.focus();
  }, [availableFrom, availableTo, onChange]);

  return (
    <div className={styles.picker}>
      <button
        ref={triggerRef}
        type="button"
        className={styles.trigger}
        onClick={toggleOpen}
        aria-expanded={isOpen}
      >
        <span className={styles.triggerIcon} aria-hidden="true">
          <CalendarIcon />
        </span>
        <span className={styles.triggerText}>
          <span className={styles.triggerLabel}>Dates</span>
          <span className={styles.triggerValue}>
            {from} to {to}
          </span>
        </span>
      </button>

      {isOpen && (
        <div className={styles.panel}>
          <div className={styles.presets}>
            {PRESETS.map((preset) => (
              <PresetButton key={preset.days} days={preset.days} onSelect={applyPreset}>
                {preset.label}
              </PresetButton>
            ))}
            <button type="button" className={styles.preset} onClick={applyFullRange}>
              Everything collected
            </button>
          </div>

          <div className={styles.monthNav}>
            <button
              type="button"
              className={styles.navButton}
              onClick={goBack}
              disabled={months[0] !== undefined && months[0] <= startOfMonth(availableFrom)}
            >
              Earlier months
            </button>
            <button
              type="button"
              className={styles.navButton}
              onClick={goForward}
              disabled={months[1] !== undefined && months[1] >= startOfMonth(availableTo)}
            >
              Later months
            </button>
          </div>

          <p className={styles.instruction} aria-live="polite">
            {pendingStart === null
              ? 'Choose the first day of the window.'
              : `Start set to ${pendingStart}. Choose the last day.`}
          </p>

          <div className={styles.months}>
            {months.map((month) => (
              <section className={styles.month} key={month} aria-label={monthLabel(month)}>
                <h3 className={styles.monthHeading}>{monthLabel(month)}</h3>
                <div className={styles.weekdays} aria-hidden="true">
                  {WEEKDAYS.map((weekday) => (
                    <span key={weekday}>{weekday.slice(0, 1)}</span>
                  ))}
                </div>
                <div className={styles.grid}>
                  {monthCells(month).map((day, index) =>
                    day === null ? (
                      // eslint-disable-next-line react/no-array-index-key -- a blank leading cell has no identity of its own
                      <span key={`blank-${String(index)}`} />
                    ) : (
                      <DayButton
                        key={day}
                        day={day}
                        isDisabled={day < availableFrom || day > availableTo}
                        isSelected={day === from || day === to || day === pendingStart}
                        isInRange={day > from && day < to}
                        onSelect={handleDayClick}
                      />
                    ),
                  )}
                </div>
              </section>
            ))}
          </div>

          <p className={styles.limit}>
            Collection runs from {availableFrom} to {availableTo}. Days outside that have no record
            behind them, so they cannot be selected.
          </p>
        </div>
      )}
    </div>
  );
}

interface PresetButtonProps {
  days: number;
  onSelect: (days: number) => void;
  children: string;
}

function PresetButton({ days, onSelect, children }: PresetButtonProps) {
  const handleClick = useCallback((): void => {
    onSelect(days);
  }, [days, onSelect]);

  return (
    <button type="button" className={styles.preset} onClick={handleClick}>
      {children}
    </button>
  );
}

interface DayButtonProps {
  day: string;
  isDisabled: boolean;
  isSelected: boolean;
  isInRange: boolean;
  onSelect: (day: string) => void;
}

function DayButton({ day, isDisabled, isSelected, isInRange, onSelect }: DayButtonProps) {
  const handleClick = useCallback((): void => {
    onSelect(day);
  }, [day, onSelect]);

  const classNames = [styles.day];
  if (isSelected) {
    classNames.push(styles.daySelected ?? '');
  } else if (isInRange) {
    classNames.push(styles.dayInRange ?? '');
  }

  return (
    <button
      type="button"
      className={classNames.join(' ')}
      onClick={handleClick}
      disabled={isDisabled}
      aria-label={dayLabel(day)}
      aria-pressed={isSelected}
    >
      {Number(day.slice(8))}
    </button>
  );
}

function CalendarIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <rect x="3.5" y="5" width="17" height="15" rx="2" />
      <path d="M3.5 10h17M8 3.5v3M16 3.5v3" />
    </svg>
  );
}
