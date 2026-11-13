import { cleanup, render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import SddBatch from './SddBatch.svelte';
const { api } = vi.hoisted(() => ({ api: { GET: vi.fn(), POST: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
beforeEach(() => {
	api.GET.mockReset();
	api.POST.mockReset();
});
afterEach(cleanup);
test('loads an exact historical batch and its owner without execution controls or probes', async () => {
	api.GET.mockResolvedValue({
		data: {
			id: 'old-batch',
			project_id: 'project',
			state: 'stopped',
			revision: 4,
			exclusion: false,
			detail: 'Execution retired',
			basis: {},
			evaluation: {},
			members: [
				{
					id: 'member',
					anchor_id: 'PROP-demo',
					state: 'canceled',
					claims: [{ id: 'claim', run_id: 'old-run', activity: 'plan', settled: false }]
				}
			]
		}
	});
	render(SddBatch, { projectId: 'project', selectedBatchId: 'old-batch' });
	expect(
		(await screen.findByRole('link', { name: 'Open retained Run' })).getAttribute('href')
	).toBe('/projects/project/runs/old-run');
	expect(screen.getByText('Retired · read only')).toBeTruthy();
	expect(api.GET).toHaveBeenCalledExactlyOnceWith(
		'/api/v1/projects/{project_id}/sdd/batches/{batch_id}',
		{ params: { path: { project_id: 'project', batch_id: 'old-batch' } } }
	);
	expect(
		screen.queryByRole('button', { name: /Create|Resume|Pause|Stop future|selection/ })
	).toBeNull();
	await userEvent.setup().click(screen.getByText('Recorded selection and outcome'));
	expect(api.POST).not.toHaveBeenCalled();
});
