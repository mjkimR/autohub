import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import DecisionNotices from './DecisionNotices.svelte';
import { decisionNoticeState } from './decision-notices.svelte';
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

const receiptCurrent = {
	channel_id: 'receipt-ui',
	revision: 9,
	destination_generation: 7,
	settings: {
		enabled: true,
		project_scope: 'all',
		project_ids: [],
		kinds: ['run-question'],
		mode: 'digest',
		review_origin: 'https://current.example',
		trusted_destination: true
	},
	channel_enabled: true,
	severity_enabled: true,
	chat_id: 'current-chat',
	observed_at: '2026-11-06T00:00:00Z'
};
test.each(['subscription', 'resend'] as const)(
	'displays immutable %s result separately from current settings',
	async (operation) => {
		const channelId = 'original-' + operation;
		const originalSettings = {
			...receiptCurrent.settings,
			mode: 'immediate',
			review_origin: 'https://original.example'
		};
		const result =
			operation === 'subscription'
				? { revision: 1, destination_generation: 2, settings: originalSettings }
				: {
						notice_id: 'original-notice',
						attempt_id: 'original-attempt',
						destination_generation: 2
					};
		const response = {
			data: {
				record_state: 'recorded',
				operation,
				request_id: 'request',
				result,
				current: receiptCurrent,
				attempt: null
			}
		};
		api.GET.mockImplementation(async (path: string) => ({
			data: path.endsWith('/decision-subscription')
				? receiptCurrent
				: {
						items: [],
						attempts: [],
						has_more: false,
						next_cursor: null,
						observed_at: receiptCurrent.observed_at
					}
		}));
		api.PUT.mockResolvedValue(response);
		api.POST.mockResolvedValue(response);
		const state = decisionNoticeState(channelId);
		if (operation === 'subscription')
			await state.save({
				...originalSettings,
				request_id: 'request',
				expected_revision: 0,
				expected_destination_generation: 2
			} as Parameters<typeof state.save>[0]);
		else
			await state.resend('original-notice', {
				request_id: 'request',
				expected_revision: 1,
				expected_destination_generation: 2,
				acknowledge_possible_duplicate: true
			});
		render(DecisionNotices, { channelId });
		await userEvent.setup().click(screen.getByRole('button', { name: 'Decision notices' }));
		if (operation === 'subscription') {
			expect(await screen.findByText('Original saved revision: 1')).toBeTruthy();
			expect(screen.getByText(/Original review origin: https:\/\/original.example/)).toBeTruthy();
		} else
			expect(await screen.findByText('Original resend attempt: original-attempt')).toBeTruthy();
		expect(screen.getByText(/Current subscription revision: 9/)).toBeTruthy();
		expect(screen.getByText(/Original destination generation: 2/)).toBeTruthy();
	}
);
test('settings review includes retained disclosure boundaries before saving', async () => {
	api.GET.mockImplementation(async (path: string) => ({
		data: path.endsWith('/decision-subscription')
			? receiptCurrent
			: { items: [], attempts: [], has_more: false, next_cursor: null }
	}));
	render(DecisionNotices, { channelId: 'disclosures' });
	await userEvent.setup().click(screen.getByRole('button', { name: 'Decision notices' }));
	expect(await screen.findByText(/at most 10 entries and 3,500 characters/)).toBeTruthy();
	expect(screen.getByText(/Neither mode guarantees a delivery deadline/)).toBeTruthy();
	expect(screen.getByText(/Hub sign-in is required/)).toBeTruthy();
	expect(screen.getByText(/Question and answer bodies are omitted/)).toBeTruthy();
	expect(screen.getByText(/Example review link/)).toBeTruthy();
});
