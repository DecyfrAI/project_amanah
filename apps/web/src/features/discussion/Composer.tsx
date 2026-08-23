import { useCallback, useState, type ChangeEvent, type FormEvent } from 'react';

import { Button } from '@/components/ui/Button';

import styles from './Composer.module.css';

interface ComposerProps {
  isSubmitting: boolean;
  onSubmit: (body: string, attachFigure: boolean) => void;
}

export function Composer({ isSubmitting, onSubmit }: ComposerProps) {
  const [body, setBody] = useState('');
  const [attachFigure, setAttachFigure] = useState(false);

  const handleSubmit = useCallback(
    (event: FormEvent<HTMLFormElement>): void => {
      event.preventDefault();
      const trimmed = body.trim();
      if (trimmed.length === 0) {
        return;
      }
      onSubmit(trimmed, attachFigure);
      setBody('');
      setAttachFigure(false);
    },
    [attachFigure, body, onSubmit],
  );

  const handleBodyChange = useCallback((event: ChangeEvent<HTMLTextAreaElement>): void => {
    setBody(event.target.value);
  }, []);

  const handleAttachChange = useCallback((event: ChangeEvent<HTMLInputElement>): void => {
    setAttachFigure(event.target.checked);
  }, []);

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <label className={styles.label} htmlFor="discussion-note">
        Add a note
      </label>
      <textarea
        id="discussion-note"
        className={styles.input}
        value={body}
        onChange={handleBodyChange}
        rows={4}
        required
      />
      <label className={styles.attach}>
        <input type="checkbox" checked={attachFigure} onChange={handleAttachChange} />
        Attach the rate figure
      </label>
      <Button variant="primary" type="submit" disabled={isSubmitting || body.trim().length === 0}>
        Post note
      </Button>
    </form>
  );
}
