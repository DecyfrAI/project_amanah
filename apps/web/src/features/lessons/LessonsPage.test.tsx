import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { LessonReaderPage } from './LessonReaderPage';
import { LESSON_CASES, LESSON_MODULES } from './lesson-copy';
import { LessonsPage } from './LessonsPage';

function renderLessons(path = '/app/lessons') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/app/lessons" element={<LessonsPage />} />
        <Route path="/app/lessons/:lessonId" element={<LessonReaderPage />} />
        <Route path="/resources" element={<LessonsPage framedForMarketing />} />
        <Route path="/resources/:lessonId" element={<LessonReaderPage framedForMarketing />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('LessonsPage', () => {
  it('lists eight syllabus titles as cards, then the resource catalog', () => {
    renderLessons();

    expect(screen.getByRole('heading', { level: 1, name: 'Lessons' })).toBeVisible();
    for (const module of LESSON_MODULES) {
      expect(screen.getByRole('heading', { name: module.title })).toBeVisible();
    }

    expect(screen.getByText('01')).toBeVisible();
    expect(screen.getByRole('link', { name: /opinion is not action/i })).toHaveTextContent(
      /9 min · 2 sources/i,
    );
    expect(screen.getByRole('heading', { name: 'Public case studies' })).toBeVisible();
    for (const entry of LESSON_CASES) {
      expect(screen.getByRole('heading', { name: entry.title })).toBeVisible();
    }
    expect(screen.getByRole('heading', { name: 'How a grievance is retargeted' })).toBeVisible();
    expect(screen.getByRole('link', { name: /Randy Borum/i })).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Resources' })).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Islamophobia Resource Center' })).toBeVisible();
    expect(screen.getByRole('heading', { name: '988 Suicide and Crisis Lifeline' })).toBeVisible();
    expect(screen.queryByRole('radio')).not.toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Category' })).toBeVisible();
    expect(screen.getByRole('combobox', { name: 'Place' })).toBeVisible();
  });

  it('opens resource links in a new tab with a visible cue', () => {
    renderLessons();

    const bridge = screen.getByRole('link', {
      name: /islamophobia resource center \(opens in a new tab\)/i,
    });
    expect(bridge).toHaveAttribute(
      'href',
      'https://bridge.georgetown.edu/projects/resource-center/',
    );
    expect(bridge).toHaveAttribute('rel', 'noopener noreferrer');
    expect(bridge).toHaveAttribute('target', '_blank');
  });

  it('filters resource cards when Place changes', async () => {
    const user = userEvent.setup();
    renderLessons();

    await user.selectOptions(screen.getByRole('combobox', { name: 'Place' }), 'uk');

    expect(screen.getByRole('heading', { name: 'Resources and reporting guidance' })).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Samaritans' })).toBeVisible();
    expect(
      screen.queryByRole('heading', { name: '988 Suicide and Crisis Lifeline' }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Hate speech policy' })).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Reddit Rules' })).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Report a post or comment' })).toBeVisible();
  });

  it('shows an actionable empty state when no resource matches', async () => {
    const user = userEvent.setup();
    renderLessons();

    await user.selectOptions(screen.getByRole('combobox', { name: 'Category' }), 'involved');
    await user.selectOptions(screen.getByRole('combobox', { name: 'Place' }), 'us');

    expect(screen.getByRole('status')).toHaveTextContent(/no reviewed resource matches/i);
    expect(screen.queryByRole('heading', { name: 'Get involved' })).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Opinion is not action' })).toBeVisible();
  });

  it('keeps the same catalog on the public resources route', () => {
    renderLessons('/resources');

    expect(screen.getByRole('heading', { level: 1, name: 'Lessons' })).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Resources' })).toBeVisible();
    expect(screen.getByRole('link', { name: /opinion is not action/i })).toHaveAttribute(
      'href',
      '/resources/01',
    );
  });

  it('opens a case study with its generated still and the inquiry note', async () => {
    const user = userEvent.setup();
    renderLessons();

    await user.click(screen.getByRole('link', { name: /christchurch masjidain/i }));

    expect(screen.getByRole('heading', { level: 1, name: 'Christchurch masjidain' })).toBeVisible();
    expect(screen.getByText(/Case study · Page 1 of/i)).toBeVisible();
    expect(
      screen.getByText(/a documented timeline is not proof that one post produced the attack/i),
    ).toBeVisible();
    expect(
      screen.getByRole('img', { name: /generated still of a quiet suburban street/i }),
    ).toHaveAttribute('src', '/media/cases/christchurch-dusk.png');
    expect(screen.queryByRole('heading', { name: 'Resources' })).not.toBeInTheDocument();
  });

  it('opens a module reader from a card and leaves the resource grid behind', async () => {
    const user = userEvent.setup();
    renderLessons();

    await user.click(screen.getByRole('link', { name: /opinion is not action/i }));

    expect(screen.getByRole('heading', { level: 1, name: 'Opinion is not action' })).toBeVisible();
    expect(
      screen.getByText(
        /radicalization of opinion and radicalization of action are different pyramids/i,
      ),
    ).toBeVisible();
    expect(screen.getByRole('button', { name: 'Sources' })).toBeVisible();
    expect(screen.queryByRole('heading', { name: 'Resources' })).not.toBeInTheDocument();
    expect(
      screen.queryByRole('heading', { name: 'How a grievance is retargeted' }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
  });

  it('does not print a chapter essay on the catalog card', () => {
    renderLessons();

    expect(
      screen.queryByText(/a common picture of radicalization is a single staircase/i),
    ).not.toBeInTheDocument();
  });

  it('names category and place on each resource card', () => {
    renderLessons();

    const card = screen.getByRole('article', { name: 'Talk Suicide Canada' });
    expect(within(card).getByText(/support for affected people · canada/i)).toBeVisible();
  });
});
