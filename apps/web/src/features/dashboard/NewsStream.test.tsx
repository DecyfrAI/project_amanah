import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { NewsStream } from './NewsStream';

function renderNews(path = '/dashboard') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <NewsStream />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('NewsStream', () => {
  it('shows a fixture headline as an outbound article link', async () => {
    renderNews();

    expect(await screen.findByRole('heading', { name: 'In the news', level: 2 })).toBeVisible();
    expect(screen.getByText(/published reporting that coincides with this window/i)).toBeVisible();

    const article = await screen.findByRole('article', {
      name: /commons hears questions on mosque safety after vandalism in a northern city/i,
    });
    const link = within(article).getByRole('link', {
      name: /commons hears questions on mosque safety after vandalism in a northern city \(opens article on BBC News\)/i,
    });

    expect(link).toHaveAttribute(
      'href',
      'https://www.bbc.co.uk/news/uk-politics-2026-08-15-mosque-safety-commons',
    );
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    expect(link).toHaveAttribute('target', '_blank');
    expect(within(article).getByText('Opens article on BBC News')).toBeVisible();
    expect(within(article).getByText('BBC News')).toBeVisible();
  });

  it('does not describe a news article as classified hate', async () => {
    renderNews();
    const section = await screen.findByRole('region', { name: /in the news/i });
    await within(section).findByRole('article', {
      name: /commons hears questions on mosque safety after vandalism in a northern city/i,
    });

    expect(within(section).queryByText(/classified as likely/i)).toBeNull();
    expect(within(section).queryByText(/caused by/i)).toBeNull();
    expect(within(section).getAllByText(/not Amanah classifications/i).length).toBeGreaterThan(0);
  });

  it('treats an empty window as a gap, not a zero finding', async () => {
    renderNews('/dashboard?from=2026-06-18&to=2026-06-20');

    expect(await screen.findByText(/no published articles sit in this window/i)).toBeVisible();
    expect(screen.queryByRole('link', { name: /opens article on/i })).toBeNull();
  });
});
