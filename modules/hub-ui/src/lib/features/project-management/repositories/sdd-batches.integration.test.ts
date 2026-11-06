import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '$lib/api';
import { SddBatches, type Batch, type Preview } from './sdd-batches.svelte';
vi.mock('$lib/api', () => ({ api: { POST: vi.fn(), GET: vi.fn() } }));
beforeEach(() => vi.clearAllMocks());
const batch = (revision: number, state = 'running'): Batch => ({
	id: 'batch',
	project_id: 'p',
	state,
	revision,
	exclusion: true,
	detail: null,
	basis: {},
	evaluation: {},
	members: []
});
it('retains the original creation payload after response loss and refuses replacement', async () => {
	const batches = new SddBatches();
	batches.project = 'p';
	vi.mocked(api.POST).mockRejectedValueOnce(new Error('response lost'));
	const preview = {
		requested_ref: 'main',
		resolved_sha: 'a'.repeat(40),
		milestone: { id: 'MS-demo', path: 'docs/roadmap/MS-demo.md' }
	} as unknown as Preview;
	const members = [
		{ id: 'PROP-a', path: 'docs/proposals/PROP-a/proposal.md', activity: 'dev' as const }
	];
	await batches.create(preview, members);
	members[0].id = 'PROP-other';
	await batches.create(preview, members);
	expect(api.POST).toHaveBeenCalledTimes(1);
	const intent = batches.pending?.create;
	expect(intent?.members[0].id).toBe('PROP-a');
	vi.mocked(api.POST).mockResolvedValueOnce({ data: batch(1) } as never);
	await batches.retry();
	const calls = vi.mocked(api.POST).mock.calls as unknown as [string, { body: unknown }][];
	expect(calls[1][1].body).toEqual(calls[0][1].body);
	expect(batches.pending).toBeNull();
});
it('ignores older control responses and replays exact control identity', async () => {
	const batches = new SddBatches();
	batches.project = 'p';
	batches.batch = batch(5, 'paused');
	vi.mocked(api.POST).mockRejectedValueOnce(new Error('lost control'));
	await batches.control('stop');
	const original = batches.pending?.control;
	batches.batch = batch(8, 'stopped');
	vi.mocked(api.POST).mockResolvedValueOnce({ data: batch(6, 'running') } as never);
	await batches.retry();
	expect(batches.batch.revision).toBe(8);
	expect(batches.batch.state).toBe('stopped');
	const calls = vi.mocked(api.POST).mock.calls as unknown as [string, { body: unknown }][];
	expect(calls[1][1].body).toEqual(original);
});

it('does not let a delayed retained list overwrite a newer stopped receipt', async () => {
	const batches = new SddBatches();
	batches.project = 'p';
	batches.batch = batch(1);
	let resolve!: (value: never) => void;
	vi.mocked(api.GET).mockImplementationOnce(
		() =>
			new Promise((done) => {
				resolve = done;
			})
	);
	const listing = batches.load('p');
	batches.batch = batch(9, 'stopped');
	resolve({ data: [batch(2, 'running')] } as never);
	await listing;
	expect(batches.batch?.state).toBe('stopped');
	expect(batches.batch?.revision).toBe(9);
});

it('confirms topological order rather than reverse click order with canonical ties', async () => {
	const { executionOrder } = await import('./sdd-batches.svelte');
	const preview = {
		complete: true,
		edges: [{ source: 'PROP-b', canonical_id: 'PROP-a' }]
	} as unknown as Preview;
	const rows = ['PROP-b', 'PROP-z', 'PROP-a'].map((id) => ({
		id,
		path: `docs/proposals/${id}/proposal.md`,
		activity: 'dev' as const
	}));
	expect(executionOrder(preview, rows).map((row) => row.id)).toEqual([
		'PROP-a',
		'PROP-b',
		'PROP-z'
	]);
});
