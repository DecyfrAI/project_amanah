import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ConnectionsPage } from './ConnectionsPage';

function connector(name: RegExp): HTMLElement {
  return screen.getByRole('article', { name });
}

describe('ConnectionsPage', () => {
  it('names the view in a single top-level heading', () => {
    render(<ConnectionsPage />);

    expect(screen.getByRole('heading', { level: 1, name: 'Connections' })).toBeVisible();
  });

  it('gives every connector a status in words, not by colour alone', () => {
    render(<ConnectionsPage />);

    expect(within(connector(/youtube data api/i)).getByText('Connected')).toBeVisible();
    expect(within(connector(/reddit api/i)).getByText('Access required')).toBeVisible();
    expect(within(connector(/mastodon/i)).getByText('Degraded')).toBeVisible();
    expect(
      within(connector(/open datapack import/i)).getByText('Not configured for scheduled runs'),
    ).toBeVisible();
  });

  it('reports collection coverage as days collected out of seven', () => {
    render(<ConnectionsPage />);

    expect(
      within(connector(/mastodon/i)).getByText(/4 of the last 7 days collected, 296 items/i),
    ).toBeVisible();
  });

  it('reports an unconfigured connector as a gap with its reason, never as zero', () => {
    render(<ConnectionsPage />);

    const reddit = within(connector(/reddit api/i));
    expect(reddit.getByText(/gap, not zero/i)).toBeVisible();
    expect(reddit.getByText(/research access has not been granted/i)).toBeVisible();
    expect(reddit.getByText('No successful run recorded')).toBeVisible();
  });

  it('says a missing source is absent from the figures rather than quiet', () => {
    render(<ConnectionsPage />);

    expect(
      within(connector(/reddit api/i)).getByText(/not evidence that Reddit is quiet/i),
    ).toBeVisible();
  });

  it('records the datapack licence, version, hash and row count', () => {
    render(<ConnectionsPage />);

    expect(screen.getByRole('link', { name: 'CC BY 4.0' })).toBeVisible();
    expect(screen.getByText('v2.1, revision 2026-05-04')).toBeVisible();
    expect(
      screen.getByText('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
    ).toBeVisible();
    expect(screen.getByText(/40,917 of 41,382/)).toBeVisible();
  });

  it('presents dataset labels as annotations rather than as predictions or reviews', () => {
    render(<ConnectionsPage />);

    expect(
      screen.getByText(/not as Amanah predictions and not as human review decisions/i),
    ).toBeVisible();
  });

  it('shows no credential and no field shaped like one', () => {
    render(<ConnectionsPage />);

    expect(screen.queryByText(/api key/i)).toBeNull();
    expect(screen.queryByText(/token/i)).toBeNull();
    expect(screen.queryByText(/secret/i)).toBeNull();
  });

  it('says the connector states are a mockup rather than readings', () => {
    render(<ConnectionsPage />);

    expect(screen.getByText('Design mockup, not a reading')).toBeVisible();
  });
});
