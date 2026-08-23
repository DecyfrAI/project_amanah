import { Outlet } from 'react-router-dom';

import { MarketingFooter } from '@/components/layout/MarketingFooter';
import { MarketingHeader } from '@/components/layout/MarketingHeader';

export function PublicLayout() {
  return (
    <>
      <MarketingHeader />
      <main id="main">
        <Outlet />
      </main>
      <MarketingFooter />
    </>
  );
}
