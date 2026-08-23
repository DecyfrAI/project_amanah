import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';

import { AppShell } from '@/components/layout/AppShell';
import { AppLoadingScreen } from '@/components/ui/AppLoadingScreen';
import { MarketingPage } from '@/pages/marketing/MarketingPage';

import { AuthGuard } from './auth-guard';
import { PublicLayout } from './PublicLayout';

const LoginPage = lazy(async () => {
  const module = await import('@/features/auth/LoginPage');
  return { default: module.LoginPage };
});

const SignUpPage = lazy(async () => {
  const module = await import('@/features/auth/SignUpPage');
  return { default: module.SignUpPage };
});

const OverviewPage = lazy(async () => {
  const module = await import('@/features/overview/OverviewPage');
  return { default: module.OverviewPage };
});

const InsightsListPage = lazy(async () => {
  const module = await import('@/features/insights/InsightsListPage');
  return { default: module.InsightsListPage };
});

const InsightPage = lazy(async () => {
  const module = await import('@/features/insights/InsightPage');
  return { default: module.InsightPage };
});

const ExplorerPage = lazy(async () => {
  const module = await import('@/features/explorer/ExplorerPage');
  return { default: module.ExplorerPage };
});

const ReviewPage = lazy(async () => {
  const module = await import('@/features/review/ReviewPage');
  return { default: module.ReviewPage };
});

const ReportsPage = lazy(async () => {
  const module = await import('@/features/reports/ReportsPage');
  return { default: module.ReportsPage };
});

const ConnectionsPage = lazy(async () => {
  const module = await import('@/features/connections/ConnectionsPage');
  return { default: module.ConnectionsPage };
});

const SettingsPage = lazy(async () => {
  const module = await import('@/features/settings/SettingsPage');
  return { default: module.SettingsPage };
});

const ProfilePage = lazy(async () => {
  const module = await import('@/features/profile/ProfilePage');
  return { default: module.ProfilePage };
});

const LessonsPage = lazy(async () => {
  const module = await import('@/features/lessons/LessonsPage');
  return { default: module.LessonsPage };
});

const LessonReaderPage = lazy(async () => {
  const module = await import('@/features/lessons/LessonReaderPage');
  return { default: module.LessonReaderPage };
});

/**
 * Two Suspense boundaries, deliberately.
 *
 * The outer one covers a cold entry into any route and shows the branded
 * loading screen. `AppShell` holds a second one around its outlet, so moving
 * between workspace tabs swaps the panel while the sidebar stays put.
 */
export function AppRouter() {
  return (
    <Suspense fallback={<AppLoadingScreen />}>
      <Routes>
        {/*
         * Only marketing and the authentication routes are anonymous. Every
         * application surface sits behind `AuthGuard`, per spec.md
         * FR-HOME-005/006 and ADR 0001, which supersedes ADR 0006. The
         * marketing door is Log in / Sign up, and the authenticated Overview
         * at `/app` is the product.
         */}
        <Route element={<PublicLayout />}>
          <Route index element={<MarketingPage />} />
          <Route path="resources" element={<LessonsPage framedForMarketing />} />
          <Route path="resources/:lessonId" element={<LessonReaderPage framedForMarketing />} />
        </Route>
        <Route path="login" element={<LoginPage />} />
        <Route path="signup" element={<SignUpPage />} />
        <Route path="app" element={<AuthGuard />}>
          <Route element={<AppShell />}>
            <Route index element={<OverviewPage />} />
            <Route path="explorer" element={<ExplorerPage />} />
            <Route path="insights" element={<InsightsListPage />} />
            <Route path="insights/:insightId" element={<InsightPage />} />
            <Route path="lessons" element={<LessonsPage />} />
            <Route path="lessons/:lessonId" element={<LessonReaderPage />} />
            <Route path="review" element={<ReviewPage />} />
            <Route path="reports" element={<ReportsPage />} />
            <Route path="connections" element={<ConnectionsPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="profile" element={<ProfilePage />} />
          </Route>
        </Route>
      </Routes>
    </Suspense>
  );
}
