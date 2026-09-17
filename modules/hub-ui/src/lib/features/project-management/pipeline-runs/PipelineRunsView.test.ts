import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import PipelineRunsView from './PipelineRunsView.svelte';

const { api } = vi.hoisted(() => ({ api: { GET: vi.fn(), POST: vi.fn() } }));

vi.mock('$lib/api', () => ({ api }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

const project = { id: 'project-1', name: 'Scheduler', enabled: true, revision: 1 };
const catalogs = [
	{
		id: 'c1',
		key: 'personal-codex',
		name: 'Personal Codex',
		enabled: true,
		pipeline_delivery: true
	},
	{ id: 'c2', key: 'old-codex', name: 'Old Codex', enabled: false, pipeline_delivery: true },
	{
		id: 'c3',
		key: 'personal-jules',
		name: 'Personal Jules',
		enabled: true,
		pipeline_delivery: false
	}
];
const run = {
	id: 'run-1',
	project_id: 'project-1',
	pull_number: 7,
	pull_url: 'https://github.com/owner/app/pull/7',
	pull_snapshot: { title: 'Ship the feature' },
	branch: 'feature/7',
	state: 'implementing',
	revision: 1,
	lease_owner: null,
	lease_expires_at: null,
	created_at: '2026-09-14T00:00:00Z'
};

beforeEach(() => {
	api.GET.mockReset();
	api.POST.mockReset();
	api.GET.mockImplementation((path: string) => {
		if (path === '/api/v1/projects') return Promise.resolve({ data: { items: [project] } });
		if (path === '/api/v1/pipeline-runs') return Promise.resolve({ data: { items: [run] } });
		if (path === '/api/v1/ai-catalogs') return Promise.resolve({ data: { items: catalogs } });
		if (path === '/api/v1/pipeline-runs/{run_id}') return Promise.resolve({ data: run });
		return Promise.resolve({ data: { items: [] } });
	});
	api.POST.mockResolvedValue({ data: { ...run, state: 'paused' } });
});

afterEach(() => {
	cleanup();
	document.body.style.removeProperty('pointer-events');
});

test('renders current run state and pauses the selected run', async () => {
	const user = userEvent.setup();
	render(PipelineRunsView);

	await screen.findByText('Ship the feature');
	expect(screen.getByText('implementing')).toBeTruthy();
	await user.click(screen.getByRole('button', { name: 'Pause Run' }));

	await waitFor(() =>
		expect(api.POST).toHaveBeenCalledWith('/api/v1/pipeline-runs/{run_id}/pause', {
			params: { path: { run_id: 'run-1' } },
			body: { reason: 'Paused via UI' }
		})
	);
});

test('enrolls the selected project and refreshes the run list', async () => {
	const user = userEvent.setup();
	render(PipelineRunsView);
	await screen.findByText('Ship the feature');
	await user.click(screen.getAllByRole('button', { name: 'Enroll PR' })[0]);
	await user.clear(screen.getByLabelText('Pull Request Number'));
	await user.type(screen.getByLabelText('Pull Request Number'), '42');
	await user.click(screen.getAllByRole('button', { name: 'Enroll PR' })[1]);

	await waitFor(() =>
		expect(api.POST).toHaveBeenCalledWith('/api/v1/projects/{project_id}/runs', {
			params: { path: { project_id: 'project-1' } },
			body: { pull_number: 42, implemented: false, catalog: null }
		})
	);
});

test('offers only enabled catalogs that deliver pull request work', async () => {
	const user = userEvent.setup();
	render(PipelineRunsView);
	await screen.findByText('Ship the feature');

	await user.click(screen.getByRole('button', { name: /Enroll PR/ }));

	const select = (await screen.findByLabelText('AI Catalog')) as HTMLSelectElement;
	expect(Array.from(select.options).map((o) => o.value)).toEqual(['', 'personal-codex']);
});

test('opens the run named in the page URL', async () => {
	window.history.replaceState({}, '', '/projects/runs?run=run-1');
	render(PipelineRunsView);

	await screen.findByText('Ship the feature');
	await waitFor(() =>
		expect(api.GET).toHaveBeenCalledWith('/api/v1/pipeline-runs/{run_id}/attempts', {
			params: { path: { run_id: 'run-1' } }
		})
	);
	window.history.replaceState({}, '', '/projects/runs');
});
