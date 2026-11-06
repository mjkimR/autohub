import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import DecisionNotices from './DecisionNotices.svelte';
const { api } = vi.hoisted(() => ({ api: { GET: vi.fn(), PUT: vi.fn(), POST: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
afterEach(() => {
	cleanup();
	document.body.style.pointerEvents = '';
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

test('direct history resend displays and binds current destination and filters', async () => {
	let generation = 3;
	let revision = 4;
	api.GET.mockImplementation(async (path: string) => ({
		data: path.endsWith('/decision-subscription')
			? {
					channel_id: 'history-ui',
					revision,
					destination_generation: generation,
					settings: {
						enabled: true,
						project_scope: 'all',
						project_ids: [],
						kinds: ['run-question'],
						mode: 'immediate',
						review_origin: 'https://hub.example',
						trusted_destination: true
					},
					channel_enabled: true,
					severity_enabled: true,
					chat_id: 'trusted-chat',
					observed_at: '2026-11-06T00:00:00Z'
				}
			: {
					items: [
						{
							id: 'notice',
							state: 'unknown',
							observed: {
								kind: 'run-question',
								project_name: 'Example project',
								run_id: 'run-identity',
								observed_at: '2026-11-06T00:00:00Z'
							},
							decision_key: 'key',
							fingerprint: 'a'.repeat(64),
							destination_generation: 3,
							created_at: '2026-11-06T00:00:00Z'
						}
					],
					attempts: [],
					has_more: false,
					next_cursor: null,
					observed_at: '2026-11-06T00:00:00Z'
				}
	}));
	render(DecisionNotices, { channelId: 'history-ui' });
	const user = userEvent.setup();
	await user.click(screen.getByRole('button', { name: 'Notice history' }));
	await user.click(await screen.findByRole('button', { name: 'Review send again' }));
	expect(screen.getByText(/trusted-chat/)).toBeTruthy();
	expect(screen.getByText(/Example project/)).toBeTruthy();
	expect(screen.getByText(/run-identity/)).toBeTruthy();
	expect(screen.getByText(/https:\/\/hub.example/)).toBeTruthy();
	const confirm = screen.getByRole('checkbox', { name: /accept a possible duplicate/ });
	await user.click(confirm);
	generation = 4;
	revision = 5;
	await user.click(screen.getByRole('button', { name: 'Refresh evidence' }));
	await waitFor(() => expect((confirm as HTMLInputElement).checked).toBe(false));
});
