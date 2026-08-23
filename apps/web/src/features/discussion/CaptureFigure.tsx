import { Link } from 'react-router-dom';

import type { DashboardCapture } from '@/api/contracts';

import styles from './CaptureFigure.module.css';

interface CaptureFigureProps {
  capture: DashboardCapture;
}

export function CaptureFigure({ capture }: CaptureFigureProps) {
  return (
    <figure className={styles.figure}>
      <img
        className={styles.image}
        src={capture.imageSrc}
        alt={capture.altText}
        width={640}
        height={360}
      />
      <figcaption className={styles.caption}>
        <Link className={styles.link} to={capture.explorerHref}>
          Open this view
        </Link>
      </figcaption>
    </figure>
  );
}
