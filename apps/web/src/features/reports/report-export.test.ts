import { describe, expect, it } from 'vitest';

import * as reportExport from './report-export';

describe('report export helpers', () => {
  it('does not build mailto or eml output, because ordinary reports go through forms', () => {
    expect(reportExport).not.toHaveProperty('mailtoHref');
    expect(reportExport).not.toHaveProperty('formatEml');
    expect(typeof reportExport.downloadText).toBe('function');
  });
});
