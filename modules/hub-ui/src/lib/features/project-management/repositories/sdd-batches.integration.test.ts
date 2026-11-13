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
