import { session } from '$lib/stores/session.svelte';
import { cleanup, render, screen } from '@testing-library/svelte';
import { afterEach, expect, test, vi } from 'vitest';
import DecisionOutcome from './DecisionOutcome.svelte';
import { decisionIntent } from './decision-intents.svelte';

vi.mock('$lib/api', () => ({ api: { GET: vi.fn(), POST: vi.fn() } }));
afterEach(() => {
	cleanup();
	session.logout();
});
const props = { head: 'h', revision: 3, onrefresh: vi.fn() };

test('without a submission the reload guidance is a collapsed secondary disclosure', () => {
	render(DecisionOutcome, { ...props, runId: 'empty-run' });
	expect(screen.queryByText('Decision outcome')).toBeNull();
	expect(screen.queryByRole('button', { name: 'Check outcome' })).toBeNull();
	const details = screen.getByText('Submitted a decision before reloading?').closest('details');
	expect(details?.open).toBe(false);
	expect(details?.textContent).toContain('not kept after a browser reload');
});

test('a retained submission shows the outcome region instead of reload guidance', () => {
	const review = decisionIntent('active-run');
	review.subject = { operation: 'answer', requestId: 'req-1' };
	render(DecisionOutcome, { ...props, runId: 'active-run' });
	expect(screen.getByRole('region', { name: 'Decision outcome' })).toBeTruthy();
	expect(screen.getByText('req-1')).toBeTruthy();
	expect(screen.getByRole('button', { name: 'Check outcome' })).toBeTruthy();
	expect(screen.queryByText('Submitted a decision before reloading?')).toBeNull();
});
