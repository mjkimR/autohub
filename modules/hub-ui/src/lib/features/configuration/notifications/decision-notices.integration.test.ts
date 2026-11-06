import { beforeEach, expect, test, vi } from 'vitest';
import { DecisionNoticeState } from './decision-notices.svelte';
const { api } = vi.hoisted(() => ({ api: { GET: vi.fn(), PUT: vi.fn(), POST: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
const current = {
	channel_id: 'channel',
	revision: 1,
	destination_generation: 2,
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
	chat_id: 'chat',
	observed_at: '2026-11-06T00:00:00Z'
};
const body = {
	...current.settings,
	request_id: 'request',
	expected_revision: 0,
	expected_destination_generation: 2
} as Parameters<DecisionNoticeState['save']>[0];
beforeEach(() => {
	vi.resetAllMocks();
	api.GET.mockImplementation(async (path: string) => ({
		data: path.endsWith('/decision-subscription')
			? current
			: {
					items: [],
					attempts: [],
					has_more: false,
					next_cursor: null,
					observed_at: current.observed_at
				}
	}));
});
test('lost response retains immutable original payload through reads and exact retry', async () => {
	const state = new DecisionNoticeState('channel');
	api.PUT.mockRejectedValueOnce(new Error('timeout'));
	await state.save(body);
	expect(state.unresolved).toBe(true);
	body.review_origin = 'https://changed.example';
	await state.load();
	api.PUT.mockResolvedValueOnce({
		data: {
			record_state: 'recorded',
			operation: 'subscription',
			request_id: 'request',
			result: { revision: 1 },
			current
		}
	});
	await state.retry();
	expect(api.PUT.mock.calls[1][1].body.review_origin).toBe('https://hub.example');
	expect(state.status).toBe('recorded');
});
test('acknowledged mutation followed by refresh failure remains recorded', async () => {
	const state = new DecisionNoticeState('channel');
	api.PUT.mockResolvedValue({
		data: {
			record_state: 'recorded',
			operation: 'subscription',
			request_id: 'request',
			result: { revision: 1 },
			current
		}
	});
	api.GET.mockRejectedValue(new Error('offline'));
	await state.save(body);
	expect(state.status).toBe('recorded');
	expect(state.error).toContain('refresh failed');
});
test('auth refusal and unknown outcome never release original intent', async () => {
	const state = new DecisionNoticeState('channel');
	api.PUT.mockResolvedValue({ error: { detail: 'forbidden' }, response: { status: 403 } });
	await state.save(body);
	expect(state.unresolved).toBe(true);
	state.dismiss();
	expect(state.intent).not.toBeNull();
	api.GET.mockResolvedValue({
		data: { record_state: 'unknown', operation: 'subscription', request_id: 'request', current }
	});
	await state.check();
	expect(state.unresolved).toBe(true);
});
test('resend replay keeps exact original target and acknowledgement', async () => {
	const state = new DecisionNoticeState('channel');
	api.POST.mockRejectedValue(new Error('lost'));
	await state.resend('notice', {
		request_id: 'retry',
		expected_revision: 1,
		expected_destination_generation: 2,
		acknowledge_possible_duplicate: true
	});
	await state.resend('different', {
		request_id: 'changed',
		acknowledge_possible_duplicate: false,
		expected_revision: 2,
		expected_destination_generation: 2
	});
	expect(api.POST).toHaveBeenCalledTimes(1);
	await state.retry();
	expect(api.POST.mock.calls[1][1].params.path.notice_id).toBe('notice');
});

test('pre-handler validation refusal allows explicitly corrected fresh request', async () => {
	const state = new DecisionNoticeState('channel');
	api.PUT.mockResolvedValueOnce({
		error: { detail: [{ type: 'value_error', loc: ['body'], msg: 'invalid settings', input: {} }] },
		response: { status: 422 }
	});
	await state.save({ ...body, request_id: 'invalid', review_origin: '' });
	expect(state.status).toBe('refused');
	state.dismiss();
	expect(state.intent).toBeNull();
	api.PUT.mockResolvedValueOnce({
		data: {
			record_state: 'recorded',
			operation: 'subscription',
			request_id: 'corrected',
			result: { revision: 1 },
			current
		}
	});
	await state.save({ ...body, request_id: 'corrected', review_origin: 'https://hub.example' });
	expect(state.status).toBe('recorded');
	expect(api.PUT).toHaveBeenCalledTimes(2);
});

test('owner-proven missing-project refusal permits fresh correction while unavailable404 stays unknown', async () => {
	const state = new DecisionNoticeState('missing-project');
	api.PUT.mockResolvedValueOnce({
		error: { code: 'DECISION_NOTICE_REFUSED', detail: 'Selected project not found' },
		response: { status: 404 }
	});
	await state.save(body);
	expect(state.status).toBe('refused');
	state.dismiss();
	api.PUT.mockResolvedValueOnce({
		data: {
			record_state: 'recorded',
			operation: 'subscription',
			request_id: 'corrected',
			result: { revision: 1 },
			current
		}
	});
	await state.save({ ...body, request_id: 'corrected' });
	expect(state.status).toBe('recorded');
	expect(api.PUT.mock.calls[1][1].body.request_id).toBe('corrected');
	const uncertain = new DecisionNoticeState('missing-channel');
	api.PUT.mockResolvedValueOnce({
		error: { code: 'DECISION_NOTICE_UNAVAILABLE' },
		response: { status: 404 }
	});
	await uncertain.save(body);
	expect(uncertain.unresolved).toBe(true);
});
