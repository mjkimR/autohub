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
