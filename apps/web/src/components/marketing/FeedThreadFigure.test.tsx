import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { FeedThreadFigure, FOCAL_COMMENT } from './FeedThreadFigure';

describe('FeedThreadFigure', () => {
  it('shows a softer unredacted remark, then buries it under unrelated posts', async () => {
    const user = userEvent.setup();
    render(<FeedThreadFigure />);

    expect(screen.getByText(/the remark arrives/i)).toBeVisible();
    expect(screen.getByText(FOCAL_COMMENT)).toBeVisible();
    expect(screen.getByText('Classified as likely anti-Muslim hate')).toBeVisible();
    expect(screen.getByText('This.')).toBeVisible();
    expect(screen.getByText('Facts.')).toBeVisible();
    expect(screen.getByText('Say it louder.')).toBeVisible();
    expect(FOCAL_COMMENT).not.toMatch(/slur/i);
    expect(screen.queryByText(/slur/i)).toBeNull();
    expect(screen.queryByRole('button', { name: /replay the refresh/i })).toBeNull();
    expect(screen.queryByRole('button', { name: /about disposable thread/i })).toBeNull();

    await user.click(screen.getByRole('button', { name: 'See more posts' }));

    expect(screen.getByText('A protest reaches the evening bulletin')).toBeVisible();
    expect(screen.getByText(FOCAL_COMMENT)).toBeVisible();
    expect(screen.getByText('Classified as likely anti-Muslim hate')).toBeInTheDocument();
    expect(screen.queryByText(/\[.*redacted\]/i)).toBeNull();
    expect(screen.getByText('This.')).toBeVisible();
    expect(screen.getByText('Weekend market was packed.')).toBeVisible();
    expect(screen.getByText(/soup recipe from last night/i)).toBeVisible();
    expect(screen.getByText(/the match starts at eight/i)).toBeVisible();
    expect(screen.getByRole('status')).toHaveTextContent('See how quickly we move on?');
    expect(screen.queryByRole('button', { name: 'See more posts' })).toBeNull();
  });
});
