import { expect, test, vi } from 'vitest';
import { SddBatches } from './sdd-batches.svelte';
const { api } = vi.hoisted(() => ({ api: { GET: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
test('a delayed previous-project history read cannot replace the selected batch', async () => {
	let finish!: (value: unknown) => void;
	api.GET.mockImplementationOnce(
		() =>
			new Promise((resolve) => {
				finish = resolve;
			})
	).mockResolvedValueOnce({ data: { id: 'current', project_id: 'new', revision: 2 } });
	const state = new SddBatches();
	state.reset('old');
	const pending = state.refresh('previous');
	state.reset('new');
	await state.refresh('current');
	finish({ data: { id: 'previous', project_id: 'old', revision: 9 } });
	await pending;
	expect(state.batch?.id).toBe('current');
});

test('old batch loads directly, list loads once and cannot replace addressed detail', async () => {
	const old = { id: 'old', project_id: 'project', revision: 1 };
	api.GET.mockReset()
		.mockResolvedValueOnce({ data: old })
		.mockResolvedValueOnce({ data: Array.from({ length: 50 }, (_, i) => ({ id: `new-${i}` })) });
	const state = new SddBatches();
	state.reset('project');
	await state.refresh('old');
	expect(api.GET.mock.calls[0][0]).toContain('/{batch_id}');
	await state.load('project');
	await state.load('project');
	expect(api.GET).toHaveBeenCalledTimes(2);
	expect(state.batch?.id).toBe('old');
	expect(state.rows).toHaveLength(51);
});

test('missing addressed B never retains A as a substitute, and a wrong-project response is rejected', async () => {
	api.GET.mockReset()
		.mockResolvedValueOnce({ data: { id: 'A', project_id: 'project' } })
		.mockResolvedValueOnce({ error: { detail: 'Not found' } })
		.mockResolvedValueOnce({ data: { id: 'B', project_id: 'other' } });
	const state = new SddBatches();
	state.reset('project');
	await state.refresh('A');
	await state.refresh('B');
	expect(state.batch).toBeNull();
	expect(state.requestedId).toBe('B');
	expect(state.error).toContain('Not found');
	await state.refresh();
	expect(state.batch).toBeNull();
	expect(state.error).toContain('does not match');
});

test('same-project address races and concurrent list reads keep the newest exact subject', async () => {
	let finish!: (value: unknown) => void;
	api.GET.mockReset()
		.mockImplementationOnce(
			() =>
				new Promise((resolve) => {
					finish = resolve;
				})
		)
		.mockResolvedValueOnce({ data: { id: 'B', project_id: 'project' } })
		.mockResolvedValueOnce({ data: [] });
	const state = new SddBatches();
	state.reset('project');
	const pending = state.refresh('A');
	await state.refresh('B');
	await state.load('project');
	finish({ data: { id: 'A', project_id: 'project' } });
	await pending;
	expect(state.batch?.id).toBe('B');
	expect(state.rows.map((row) => row.id)).toEqual(['B']);
});

test('successful list load preserves the failed addressed subject error and independent list failures', async () => {
	api.GET.mockReset()
		.mockResolvedValueOnce({ error: { detail: 'Not found' } })
		.mockResolvedValueOnce({ data: [] });
	const state = new SddBatches();
	state.reset('project');
	await state.refresh('missing');
	await state.load('project');
	expect(state.requestedId).toBe('missing');
	expect(state.batch).toBeNull();
	expect(state.error).toContain('Not found');
	expect(state.loaded).toBe(true);
});
