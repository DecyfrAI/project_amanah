import { useEffect } from 'react';

export function usePageTitle(title: string): void {
  useEffect(() => {
    document.title = `${title} · Project Amanah`;
  }, [title]);
}
