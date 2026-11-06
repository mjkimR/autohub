import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import DecisionNotices from './DecisionNotices.svelte';
const { api } = vi.hoisted(() => ({ api: { GET: vi.fn(), PUT: vi.fn(), POST: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
afterEach(() => {
	cleanup();
	vi.resetAllMocks();
});
test('explicit trust confirmation clears when review origin changes', async () => {
	api.GET.mockImplementation(async (path: string) => ({
		data: path.endsWith('/decision-subscription')
			? {
					channel_id: 'ui',
					revision: 0,
					destination_generation: 0,
					settings: {
						enabled: false,
						project_scope: 'all',
						project_ids: [],
						kinds: ['run-question'],
						mode: 'immediate',
						review_origin: 'https://hub.example',
						trusted_destination: false
					},
					channel_enabled: true,
					severity_enabled: true,
					chat_id: 'chat',
					observed_at: '2026-11-06T00:00:00Z'
				}
			: { items: [], attempts: [], has_more: false, next_cursor: null }
	}));
	render(DecisionNotices, { channelId: 'ui' });
	const user = userEvent.setup();
	await user.click(screen.getByRole('button', { name: 'Decision notices' }));
	const trust = await screen.findByRole('checkbox', { name: /I reviewed these settings/ });
	await user.click(trust);
	expect((trust as HTMLInputElement).checked).toBe(true);
	await user.type(screen.getByRole('textbox', { name: 'Hub review origin' }), '/changed');
	await waitFor(() => expect((trust as HTMLInputElement).checked).toBe(false));
	await user.click(screen.getAllByRole('button', { name: 'Close' })[0]);
	await waitFor(() => expect(document.body.style.pointerEvents).not.toBe('none'));
	await user.click(screen.getByRole('button', { name: 'Notice history' }));
	expect(screen.getByText(/Unknown outcomes are never automatically resent/)).toBeTruthy();
});
