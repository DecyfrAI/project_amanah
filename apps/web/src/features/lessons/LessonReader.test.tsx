import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { LessonReaderPage } from './LessonReaderPage';
import { LessonsPage } from './LessonsPage';

function renderReader(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/app/lessons" element={<LessonsPage />} />
        <Route path="/app/lessons/:lessonId" element={<LessonReaderPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('LessonReaderPage', () => {
  it('shows the thesis and a Sources chapter with outbound citations', async () => {
    const user = userEvent.setup();
    renderReader('/app/lessons/01');

    expect(document.title).toMatch(/01 Opinion is not action/i);
    expect(screen.getByText(/this module summarizes published research/i)).toBeVisible();
    expect(
      screen.getByText(
        /radicalization of opinion and radicalization of action are different pyramids/i,
      ),
    ).toBeVisible();

    await user.click(screen.getByRole('button', { name: 'Sources' }));

    expect(screen.getByRole('heading', { level: 2, name: 'Sources' })).toBeVisible();
    const doi = screen.getByRole('link', { name: /DOI 10\.1037\/amp0000062/i });
    expect(doi).toHaveAttribute('href', 'https://doi.org/10.1037/amp0000062');
    expect(doi).toHaveAttribute('rel', 'noopener noreferrer');
    expect(doi).toHaveAttribute('target', '_blank');
  });

  it('turns pages with next, previous, and arrow keys', async () => {
    const user = userEvent.setup();
    renderReader('/app/lessons/01');

    expect(screen.getByRole('heading', { name: 'Two pyramids, not one ladder' })).toBeVisible();

    await user.click(screen.getByRole('button', { name: 'Next page' }));
    expect(
      screen.getByRole('heading', { name: 'Most radical opinion never becomes action' }),
    ).toBeVisible();

    await user.keyboard('{ArrowRight}');
    expect(screen.getByRole('heading', { name: 'The puzzle is not a missing step' })).toBeVisible();

    await user.keyboard('{ArrowLeft}');
    expect(
      screen.getByRole('heading', { name: 'Most radical opinion never becomes action' }),
    ).toBeVisible();

    await user.click(screen.getByRole('button', { name: 'Previous page' }));
    expect(screen.getByRole('heading', { name: 'Two pyramids, not one ladder' })).toBeVisible();
  });

  it('renders an actionable error for an unknown module', () => {
    renderReader('/app/lessons/not-a-module');

    expect(screen.getByRole('alert')).toHaveTextContent(/not in Lessons/i);
    expect(screen.getByRole('link', { name: 'Back to Lessons' })).toHaveAttribute(
      'href',
      '/app/lessons',
    );
    expect(
      screen.queryByRole('heading', { name: 'Opinion is not action' }),
    ).not.toBeInTheDocument();
  });

  it('names 4chan without linking there', async () => {
    const user = userEvent.setup();
    renderReader('/app/lessons/06');

    await user.click(screen.getByRole('button', { name: /naming narrower rooms/i }));

    expect(screen.getAllByText(/4chan and 8chan/i).length).toBeGreaterThan(0);
    expect(screen.queryByRole('link', { name: /4chan|8chan/i })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Exercise: what the paper found' }));

    expect(screen.getAllByText(/this page does not link to them/i).length).toBeGreaterThan(0);
    const hrefs = screen
      .getAllByRole('link')
      .map((link) => link.getAttribute('href') ?? '')
      .join('\n');
    expect(hrefs).not.toMatch(/4chan|8chan|8kun/i);
  });

  it('reuses the mindset figure in module 03', async () => {
    const user = userEvent.setup();
    renderReader('/app/lessons/03');

    await user.click(screen.getByRole('button', { name: 'Four movements in the sketch' }));

    expect(screen.getByRole('button', { name: /grievance/i })).toBeVisible();
    expect(screen.getByText(/a published model/i)).toBeVisible();
  });

  it('places a distinct exercise with a named control on sampled modules', async () => {
    const user = userEvent.setup();
    renderReader('/app/lessons/01');

    await user.click(screen.getByRole('button', { name: 'Exercise: opinion or action' }));

    expect(screen.getAllByRole('button', { name: 'Opinion pyramid' }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole('button', { name: 'Action pyramid' }).length).toBeGreaterThan(0);
  });

  it('adds a stage exercise beside the Borum figure in module 03', async () => {
    const user = userEvent.setup();
    renderReader('/app/lessons/03');

    await user.click(screen.getByRole('button', { name: 'Exercise: which stage is this remark?' }));

    expect(screen.getAllByRole('button', { name: /1 grievance/i }).length).toBeGreaterThan(0);
  });

  it('shows the isolation still and a vantage toggle in module 04', async () => {
    const user = userEvent.setup();
    renderReader('/app/lessons/04');

    expect(screen.getByRole('img', { name: /silhouette facing a bright screen/i })).toBeVisible();
    expect(screen.getByText(/ordinary night at a screen/i)).toBeVisible();
    expect(
      screen.queryByText(/not a photograph of anyone in this sample/i),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/still is from the Path section/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Exercise: in the room, or outside it' }));

    expect(screen.getByRole('button', { name: 'In the room' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Outside the room' })).toBeVisible();
  });

  it('asks whether a German Facebook coefficient can be imported', async () => {
    const user = userEvent.setup();
    renderReader('/app/lessons/07');

    await user.click(
      screen.getByRole('button', { name: 'Exercise: can this coefficient travel?' }),
    );

    expect(screen.getByRole('button', { name: 'Yes' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'No' })).toBeVisible();
  });

  it('explains a wrong scoped sentence instead of leaving it as a silent miss', async () => {
    const user = userEvent.setup();
    renderReader('/app/lessons/08');

    await user.click(screen.getByRole('button', { name: 'Exercise: which sentence is allowed?' }));
    await user.click(screen.getByRole('button', { name: /muslims are more hated in march/i }));

    expect(screen.getByRole('status')).toHaveTextContent(/claim about a people/i);
    expect(
      screen.getByRole('button', {
        name: /in this sample, 12 comments were classified as likely/i,
      }),
    ).toBeVisible();
  });

  it('explains a wrong coefficient import as a category error', async () => {
    const user = userEvent.setup();
    renderReader('/app/lessons/07');

    await user.click(
      screen.getByRole('button', { name: 'Exercise: can this coefficient travel?' }),
    );
    await user.click(screen.getByRole('button', { name: 'Yes' }));

    expect(screen.getByRole('status')).toHaveTextContent(/category error/i);
  });
});
