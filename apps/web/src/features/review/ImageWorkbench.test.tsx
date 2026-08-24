import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { ImageWorkbench } from './ImageWorkbench';

function renderWorkbench() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: 0 }, mutations: { retry: 0 } },
  });

  return render(
    <QueryClientProvider client={client}>
      <ImageWorkbench />
    </QueryClientProvider>,
  );
}

function imageFile(name = 'capture.png'): File {
  return new File([new Uint8Array(64)], name, { type: 'image/png' });
}

describe('ImageWorkbench', () => {
  it('offers labelling and testing as separate paths, saying which one saves', () => {
    renderWorkbench();

    expect(screen.getByRole('radio', { name: /Label an image/ })).toBeChecked();
    expect(screen.getByRole('radio', { name: /Test the model/ })).not.toBeChecked();
    expect(
      screen.getByText(/Record a training annotation for later fine-tuning. This is saved./),
    ).toBeVisible();
    expect(
      screen.getByText(/See how the classifier reads an image.*Nothing is saved/s),
    ).toBeVisible();
  });

  it('opens on the labelling path, so testing is a deliberate choice', () => {
    renderWorkbench();

    expect(screen.getByLabelText('Research image')).toBeVisible();
    expect(screen.queryByLabelText('Image to test')).toBeNull();
  });

  it('switches to the test path and offers no label controls there', async () => {
    const user = userEvent.setup();
    renderWorkbench();

    await user.click(screen.getByRole('radio', { name: /Test the model/ }));

    expect(screen.getByLabelText('Image to test')).toBeVisible();
    // Nothing on this path can record a label.
    expect(screen.queryByRole('button', { name: 'Save training label' })).toBeNull();
    expect(screen.queryByLabelText('Research image')).toBeNull();
  });

  it('answers in ordinary words rather than taxonomy field names', async () => {
    const user = userEvent.setup();
    renderWorkbench();

    await user.click(screen.getByRole('radio', { name: /Test the model/ }));
    await user.upload(screen.getByLabelText('Image to test'), imageFile());

    expect(await screen.findByRole('heading', { name: 'What the model made of it' })).toBeVisible();
    // A sentence, not `stance: likely_anti_muslim`.
    expect(screen.getByText(/^The model (thinks|could not settle)/)).toBeVisible();
    expect(screen.queryByText('likely_anti_muslim')).toBeNull();
    expect(screen.queryByText('muslim_related')).toBeNull();
  });

  it('says the fixture stub did not open the file, so a name change is not a new reading', async () => {
    const user = userEvent.setup();
    renderWorkbench();

    await user.click(screen.getByRole('radio', { name: /Test the model/ }));
    await user.upload(screen.getByLabelText('Image to test'), imageFile());

    expect(
      await screen.findByText('This is a rehearsal, not a reading of your image'),
    ).toBeVisible();
    expect(screen.getByText(/does not open the file/i)).toBeVisible();
    expect(screen.getByText(/renaming an image changes the answer/i)).toBeVisible();
  });

  it('says a score is not a probability that the answer is right', async () => {
    const user = userEvent.setup();
    renderWorkbench();

    await user.click(screen.getByRole('radio', { name: /Test the model/ }));
    await user.upload(screen.getByLabelText('Image to test'), imageFile());

    expect(
      await screen.findByText(/not a probability that the answer is\s+correct/i),
    ).toBeVisible();
    expect(screen.getByText(/this is a proposal and not a finding/i)).toBeVisible();
    expect(screen.getByText(/Nothing here was saved/i)).toBeVisible();
  });

  it('clears the result so a second image starts from nothing', async () => {
    const user = userEvent.setup();
    renderWorkbench();

    await user.click(screen.getByRole('radio', { name: /Test the model/ }));
    await user.upload(screen.getByLabelText('Image to test'), imageFile());
    await screen.findByRole('heading', { name: 'What the model made of it' });

    await user.click(screen.getByRole('button', { name: 'Clear and try another' }));

    expect(screen.queryByRole('heading', { name: 'What the model made of it' })).toBeNull();
    expect(screen.getByLabelText('Image to test')).toBeVisible();
  });

  it('refuses a file the evidence rules reject, without asking the model', async () => {
    const user = userEvent.setup();
    renderWorkbench();

    await user.click(screen.getByRole('radio', { name: /Test the model/ }));
    const pdf = new File([new Uint8Array(64)], 'notes.pdf', { type: 'application/pdf' });
    await user.upload(screen.getByLabelText('Image to test'), pdf);

    expect(screen.queryByRole('heading', { name: 'What the model made of it' })).toBeNull();
  });
});
