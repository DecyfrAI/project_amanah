/**
 * A failure at the data boundary that is safe to show.
 *
 * Views render `message` and never the underlying exception. Live-provider
 * mapping strips provider wording before it reaches here.
 */
export class ApiRequestError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiRequestError';
    this.status = status;
  }
}
