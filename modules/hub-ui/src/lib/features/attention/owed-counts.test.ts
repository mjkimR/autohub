import { beforeEach, expect, test, vi } from 'vitest';
import { session } from '$lib/stores/session.svelte';
import {
	decisionPhrase,
	decisionText,
	owedPhrase,
	owedText,
	OwedCountsStore,
	summarizeOwedCounts
} from './owed-counts.svelte';

test('uses the exact counted total and the decision part of the same response', () => {
	const value = summarizeOwedCounts({
		total: 7,
		by_kind: { decision: 2, 'stopped-run': 5, 'failed-run': 3 },
		by_project: { p1: 7 }
	});
	expect(value).toEqual({
		status: 'known',
		total: 7,
		byKind: { decision: 2, 'stopped-run': 5, 'failed-run': 3 },
		byProject: { p1: 7 }
	});
	expect(owedText(value)).toBe('7');
	expect(owedPhrase(value)).toBe('7 items need you');
	expect(decisionText(value)).toBe('2');
	expect(decisionPhrase(value)).toBe('2 pending decisions');
});

test('zero and unknown carry no text', () => {
	const zero = summarizeOwedCounts({ total: 0, by_kind: { 'failed-run': 4 }, by_project: {} });
	expect(zero.status).toBe('known');
	for (const value of [zero, { status: 'unknown' } as const]) {
		expect(owedText(value)).toBe('');
		expect(owedPhrase(value)).toBe('');
		expect(decisionText(value)).toBe('');
		expect(decisionPhrase(value)).toBe('');
	}
});

test('singular phrases', () => {
	const value = summarizeOwedCounts({ total: 1, by_kind: { decision: 1 }, by_project: {} });
	expect(owedPhrase(value)).toBe('1 item needs you');
	expect(decisionPhrase(value)).toBe('1 pending decision');
});

test.each([undefined, -1, 1.5, Number.NaN])('an invalid total (%s) is unknown', (total) => {
	expect(summarizeOwedCounts({ total, by_kind: {}, by_project: {} } as never)).toEqual({
		status: 'unknown'
	});
});

test('a missing response is unknown and invalid per-kind values are dropped', () => {
	expect(summarizeOwedCounts(undefined)).toEqual({ status: 'unknown' });
	const value = summarizeOwedCounts({
		total: 2,
		by_kind: { decision: -3, 'stopped-run': 2 },
		by_project: {}
	});
	expect(value).toMatchObject({ byKind: { 'stopped-run': 2 } });
});

const { api } = vi.hoisted(() => ({ api: { GET: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
beforeEach(() => api.GET.mockReset());
const known = { total: 2, by_kind: { decision: 1 }, by_project: { p1: 2 } };
const fallback = 'Needs-you counts are unavailable';
function pendingResponse() {
	let resolve!: (result: unknown) => void;
	const promise = new Promise((done) => {
		resolve = done;
	});
	return { promise, resolve };
}

test('store begins unknown without an error and retains a failed reason until recovery settles', async () => {
	const store = new OwedCountsStore();
	expect(store.value.status).toBe('unknown');
	expect(store.error).toBe('');
	api.GET.mockResolvedValueOnce({ error: { detail: 'Database busy' } });
	await store.refresh();
	expect(store.value.status).toBe('unknown');
	expect(store.error).toBe('Database busy');
	const pending = pendingResponse();
	api.GET.mockReturnValueOnce(pending.promise);
	const refresh = store.refresh();
	expect(store.error).toBe('Database busy');
	await store.refresh(); // The existing in-flight guard adds no duplicate request.
	expect(api.GET).toHaveBeenCalledTimes(2);
	pending.resolve({ data: known });
	await refresh;
	expect(store.value).toMatchObject({ status: 'known', total: 2 });
	expect(store.error).toBe('');
});

test('API errors take precedence over accompanying data and use existing validation messages', async () => {
	const store = new OwedCountsStore();
	api.GET.mockResolvedValueOnce({
		data: known,
		error: { detail: [{ msg: 'Not ready', input: 'hidden' }] }
	});
	await store.refresh();
	expect(store.value.status).toBe('unknown');
	expect(store.error).toBe('Not ready');
});

test.each([
	{ error: { detail: '' } },
	{ data: undefined },
	{ data: { total: -1 } },
	{ data: { total: 1.5 } }
])('unavailable responses use a bounded reason (%j)', async (response) => {
	const store = new OwedCountsStore();
	api.GET.mockResolvedValueOnce(response);
	await store.refresh();
	expect(store.value.status).toBe('unknown');
	expect(store.error).toBe(fallback);
});

test('thrown failures use the bounded reason and later zero counts clear it', async () => {
	const store = new OwedCountsStore();
	api.GET.mockRejectedValueOnce(new Error('internal diagnostic'));
	await store.refresh();
	expect(store.error).toBe(fallback);
	api.GET.mockResolvedValueOnce({ data: { total: 0, by_kind: {}, by_project: {} } });
	await store.refresh();
	expect(store.value).toMatchObject({ status: 'known', total: 0 });
	expect(store.error).toBe('');
});

test.each([{ data: known }, { error: { detail: 'Old failure' } }])(
	'an obsolete session response cannot replace current counts or reason (%j)',
	async (response) => {
		const store = new OwedCountsStore();
		const pending = pendingResponse();
		api.GET.mockReturnValueOnce(pending.promise);
		const refresh = store.refresh();
		session.logout();
		store.value = { status: 'known', total: 7, byKind: {}, byProject: { p2: 7 } };
		store.error = 'Current reason';
		pending.resolve(response);
		await refresh;
		expect(store.value).toMatchObject({ status: 'known', total: 7, byProject: { p2: 7 } });
		expect(store.error).toBe('Current reason');
	}
);
