import styles from './Avatar.module.css';

interface AvatarProps {
  displayName: string;
  imageSrc: string | null;
  size?: 'small' | 'medium' | 'large';
}

/**
 * Initials from the first and last word of a name.
 *
 * One letter for a single-word name, and an empty string for an empty name, in
 * which case the caller still shows a labelled circle rather than a blank.
 */
export function initialsFor(displayName: string): string {
  const words = displayName
    .trim()
    .split(/\s+/)
    .filter((word) => word !== '');

  if (words.length === 0) {
    return '';
  }

  const first = words[0]?.charAt(0) ?? '';
  const last = words.length > 1 ? (words[words.length - 1]?.charAt(0) ?? '') : '';
  return `${first}${last}`.toUpperCase();
}

/**
 * The person's picture, or their initials when there is none.
 *
 * Decorative in both cases: it always sits beside the name it represents, so
 * announcing it again would only repeat what the reader just heard. The initials
 * are not a substitute for the name, which is why nothing here is the accessible
 * label for a control.
 */
export function Avatar({ displayName, imageSrc, size = 'medium' }: AvatarProps) {
  if (imageSrc !== null) {
    return <img className={`${styles.avatar} ${styles[size]}`} src={imageSrc} alt="" />;
  }

  return (
    <span className={`${styles.avatar} ${styles.initials} ${styles[size]}`} aria-hidden="true">
      {initialsFor(displayName)}
    </span>
  );
}
