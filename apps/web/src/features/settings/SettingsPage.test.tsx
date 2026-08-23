import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { SettingsPage } from './SettingsPage';

describe('SettingsPage', () => {
  it('names the view in a single top-level heading', () => {
    render(<SettingsPage />);

    expect(screen.getByRole('heading', { level: 1, name: 'Settings' })).toBeVisible();
  });

  it('groups the safety controls under a legend', () => {
    render(<SettingsPage />);

    expect(screen.getByRole('group', { name: 'What you see by default' })).toBeVisible();
    expect(screen.getByRole('group', { name: 'Row height in research tables' })).toBeVisible();
  });

  it('starts with media blurring on, and does not offer text redaction', () => {
    render(<SettingsPage />);

    expect(
      screen.getByRole('checkbox', { name: 'Blur media until I choose to view it' }),
    ).toBeChecked();
    expect(screen.getByText(/Media stays blurred until revealed/)).toBeVisible();
    expect(screen.queryByRole('checkbox', { name: /redact slurs/i })).toBeNull();
    expect(screen.getByText(/comment wording is shown in full/i)).toBeVisible();
  });

  it('turning the media blur off is reflected in the summary', async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);

    await user.click(
      screen.getByRole('checkbox', { name: 'Blur media until I choose to view it' }),
    );

    expect(screen.getByText(/Media appears unblurred/i)).toBeVisible();
  });

  it('starts at comfortable density and changes the sample table when compact is chosen', async () => {
    const user = userEvent.setup();
    render(<SettingsPage />);

    const comfortable = screen.getByRole('radio', { name: 'Comfortable' });
    const compact = screen.getByRole('radio', { name: 'Compact' });
    expect(comfortable).toBeChecked();

    const before = screen.getByRole('table').className;
    await user.click(compact);

    expect(compact).toBeChecked();
    expect(comfortable).not.toBeChecked();
    expect(screen.getByRole('table').className).not.toBe(before);
  });

  it('shows the model score as a score rather than as a proportion', () => {
    render(<SettingsPage />);

    const row = screen.getByRole('row', { name: /itm_7fb2c9/ });
    expect(row).toHaveTextContent('0.58');
    expect(row).not.toHaveTextContent('%');
  });

  it('says plainly that none of these choices is saved', () => {
    render(<SettingsPage />);

    expect(screen.getAllByText(/not saved between visits/i)).toHaveLength(2);
  });

  it('points at the sidebar for the theme rather than repeating the control', () => {
    render(<SettingsPage />);

    expect(screen.getByRole('heading', { level: 2, name: 'Theme' })).toBeVisible();
    expect(screen.getByText(/toggle lives at the foot of the sidebar/i)).toBeVisible();
    expect(screen.queryByRole('radio', { name: /dark/i })).toBeNull();
  });
});
