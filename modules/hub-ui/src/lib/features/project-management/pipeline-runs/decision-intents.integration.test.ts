import { describe, it, expect, vi, beforeEach } from 'vitest';
import { decisionIntent } from './decision-intents.svelte';
import { api } from '$lib/api';
vi.mock('$lib/api', () => ({ api: { POST: vi.fn(), GET: vi.fn() } }));

describe('immutable decision continuation', () => {
	beforeEach(() => vi.clearAllMocks());
	it('retains original body across close/reopen and refresh, blocking a replacement request', async () => {
		const review = decisionIntent('uncertain-run');
		vi.mocked(api.POST).mockRejectedValueOnce(new Error('lost response'));
		const body = { request_id: 'original', expected_revision: 4, answer_id: 'answer' };
		await expect(review.submit('resume', body, 'head')).rejects.toThrow('lost response');
		body.expected_revision = 99;
		expect(decisionIntent('uncertain-run')).toBe(review);
		await expect(
			review.submit('resume', { ...body, request_id: 'replacement' }, 'head')
		).rejects.toThrow('original outcome');
		vi.mocked(api.POST).mockResolvedValueOnce({ data: {} } as never);
		vi.mocked(api.GET).mockResolvedValueOnce({ data: { record_state: 'recorded' } } as never);
		await review.retry('head');
		expect(
			(vi.mocked(api.POST).mock.calls as unknown as [string, { body: unknown }][])[1][1].body
		).toEqual({
			request_id: 'original',
			expected_revision: 4,
			answer_id: 'answer'
		});
		expect(review.intent?.acknowledged).toBe(true);
	});
	it('keeps acknowledged result after read failure and refuses changed-basis replay', async () => {
		const review = decisionIntent('acknowledged-run');
		vi.mocked(api.POST).mockResolvedValueOnce({ data: {} } as never);
		vi.mocked(api.GET).mockRejectedValueOnce(new Error('read unavailable'));
		await review.submit('resume', { request_id: 'one', expected_revision: 1 }, 'old');
		expect(review.intent?.acknowledged).toBe(true);
		expect(review.error).toContain('Refresh failed');
		await review.retry('changed');
		expect(api.POST).toHaveBeenCalledTimes(1);
	});
});

it('distinguishes definitive rejection from publication-in-progress and keeps history subject separate', async () => {
	const review = decisionIntent('rejected-run');
	vi.mocked(api.POST).mockResolvedValueOnce({
		error: {
			code: 'INVALID_REQUEST',
			detail: [{ loc: ['body', 'feedback'], msg: 'Invalid input' }]
		},
		response: { status: 422 }
	} as never);
	await expect(
		review.submit('resume', { request_id: 'bad', expected_revision: 1 }, 'head')
	).rejects.toThrow();
	expect(review.intent?.rejected).toBe(true);
	review.releaseRejection();
	vi.mocked(api.POST).mockResolvedValueOnce({
		error: { code: 'SDD_DECISION_IN_PROGRESS' },
		response: { status: 409 }
	} as never);
	await expect(
		review.submit('resume', { request_id: 'pending', expected_revision: 2 }, 'head')
	).rejects.toThrow();
	expect(review.unresolved).toBe(true);
	expect(review.intent?.rejected).not.toBe(true);
	vi.mocked(api.GET).mockResolvedValue({
		data: { request_id: 'history', operation: 'answer', record_state: 'recorded' }
	} as never);
	await review.check('answer', 'history');
	expect(review.subject).toEqual({ operation: 'answer', requestId: 'history' });
	expect(review.intent?.requestId).toBe('pending');
	expect(review.displayingIntent).toBe(false);
	await review.check();
	expect(vi.mocked(api.GET).mock.lastCall?.[1]).toMatchObject({
		params: { path: { request_id: 'history' }, query: { operation: 'answer' } }
	});
	const recovery = decisionIntent('rejected-run', true);
	expect(recovery.unresolved).toBe(false);
	expect(recovery).not.toBe(review);
});

it('retains runner timeout422 candidate uncertainty and blocks original mutation during lost recovery', async () => {
	const review = decisionIntent('timeout-run');
	vi.mocked(api.POST).mockResolvedValueOnce({
		error: {
			code: 'INVALID_REQUEST',
			detail: 'SDD runner unavailable or timed out; provision Git and the pinned CLI'
		},
		response: { status: 422 }
	} as never);
	await expect(
		review.submit(
			'resume',
			{
				request_id: 'original',
				expected_revision: 1,
				decision: 'accept_plan',
				head_sha: 'a'.repeat(40)
			},
			'head'
		)
	).rejects.toThrow();
	expect(review.intent?.rejected).not.toBe(true);
	const history = decisionIntent('history-recovery-run');
	const recovery = decisionIntent('history-recovery-run', true);
	vi.mocked(api.POST).mockRejectedValueOnce(new Error('lost recovery response'));
	await expect(
		recovery.submit('resume', { request_id: 'recovery', expected_revision: 2 }, 'head')
	).rejects.toThrow();
	await expect(
		history.submit(
			'resume',
			{ request_id: 'competing', expected_revision: 2, decision: 'approve' },
			'head'
		)
	).rejects.toThrow('original outcome');
});

it('blocks competing original mutation while recovery response is unknown after history selection', async () => {
	const original = decisionIntent('recovery-lock-run');
	const recovery = decisionIntent('recovery-lock-run', true);
	vi.mocked(api.POST).mockRejectedValueOnce(new Error('lost recovery'));
	await expect(
		recovery.submit('resume', { request_id: 'recovery-one', expected_revision: 1 }, 'head')
	).rejects.toThrow();
	await expect(
		original.submit('resume', { request_id: 'competing-one', expected_revision: 1 }, 'head')
	).rejects.toThrow('original outcome');
});
