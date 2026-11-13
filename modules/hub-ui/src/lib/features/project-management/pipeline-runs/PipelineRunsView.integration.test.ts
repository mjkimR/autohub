import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import PipelineRunsView from './PipelineRunsView.svelte';

const { api, goto } = vi.hoisted(() => ({ api: { GET: vi.fn(), POST: vi.fn() }, goto: vi.fn() }));

vi.mock('$lib/api', () => ({ api }));
vi.mock('$app/navigation', () => ({ goto }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

/**
 * Opens a row's overflow menu. Floating UI cannot measure layout in jsdom, so the positioned menu
 * stays visibility-hidden there and its items are queried with `hidden: true`.
 */
async function openMenu(user: ReturnType<typeof userEvent.setup>) {
	await user.click(screen.getByRole('button', { name: 'More actions for PR #7' }));
	await screen.findByRole('menu', { hidden: true });
}

/** A hidden element has no computed accessible name, so menu items are matched by text. */
function menuItems() {
	return screen
		.getAllByRole('menuitem', { hidden: true })
		.map((item) => [item.textContent?.trim(), item] as const);
}
function menuItem(name: string) {
	const found = menuItems().find(([text]) => text === name)?.[1];
	if (!found) throw new Error(`No menu item ${name}`);
	return found;
}

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

test('combines inherited group and run state filters, preserving the empty null query', async () => {
	render(PipelineRunsView);
	await screen.findByText('Ship the feature');
	await fireEvent.change(screen.getByLabelText('Run state'), { target: { value: 'blocked' } });
	await fireEvent.change(screen.getByLabelText('Run group'), { target: { value: 'null' } });
	await waitFor(() =>
		expect(api.GET).toHaveBeenCalledWith('/api/v1/pipeline-runs', {
			params: { query: expect.objectContaining({ group_key: '', state: 'blocked', offset: 0 }) }
		})
	);
	await fireEvent.change(screen.getByLabelText('Run group'), { target: { value: 'key' } });
	await fireEvent.input(screen.getByLabelText('Run group key'), { target: { value: ' game-a ' } });
	await waitFor(() =>
		expect(api.GET).toHaveBeenCalledWith('/api/v1/pipeline-runs', {
			params: {
				query: expect.objectContaining({ group_key: 'game-a', state: 'blocked', offset: 0 })
			}
		})
	);
	await fireEvent.change(screen.getByLabelText('Run group'), { target: { value: 'all' } });
	await waitFor(() =>
		expect(api.GET.mock.calls.filter(([path]) => path === '/api/v1/pipeline-runs').at(-1)).toEqual([
			'/api/v1/pipeline-runs',
			{
				params: {
					query: expect.objectContaining({ group_key: undefined, state: 'blocked', offset: 0 })
				}
			}
		])
	);
});

beforeEach(() => {
	api.GET.mockReset();
	api.POST.mockReset();
	goto.mockReset();
	api.GET.mockImplementation((path: string) => {
		if (path === '/api/v1/projects')
			return Promise.resolve({ data: { items: [project], total_count: 1 } });
		if (path === '/api/v1/pipeline-runs')
			return Promise.resolve({ data: { items: [run], total_count: 1 } });
		if (path === '/api/v1/ai-catalogs') return Promise.resolve({ data: { items: catalogs } });
		if (path === '/api/v1/pipeline-runs/{run_id}') return Promise.resolve({ data: run });
		return Promise.resolve({ data: { items: [] } });
	});
	api.POST.mockResolvedValue({ data: { ...run, state: 'paused' } });
});

afterEach(() => {
	cleanup();
	vi.restoreAllMocks();
	document.body.style.removeProperty('pointer-events');
});

test('renders current run state and pauses the selected run', async () => {
	const user = userEvent.setup();
	render(PipelineRunsView);

	await screen.findByText('Ship the feature');
	expect(screen.getByText('Implementing', { selector: '[data-run-state]' })).toBeTruthy();
	await openMenu(user);
	await user.click(menuItem('Pause'));

	await waitFor(() =>
		expect(api.POST).toHaveBeenCalledWith('/api/v1/pipeline-runs/{run_id}/pause', {
			params: { path: { run_id: 'run-1' } },
			body: { reason: 'Paused via UI' }
		})
	);
});

test.each([
	{ label: 'Advance now', state: 'implementing', action: 'advance', menu: true },
	{ label: 'Resume', state: 'paused', action: 'resume', menu: false },
	{ label: 'Cancel run', state: 'implementing', action: 'cancel', menu: true }
])(
	'$label acts on the selected row and refreshes the list',
	async ({ label, state, action, menu }) => {
		const previous = api.GET.getMockImplementation()!;
		api.GET.mockImplementation((path: string) =>
			path === '/api/v1/pipeline-runs'
				? Promise.resolve({ data: { items: [{ ...run, state }], total_count: 1 } })
				: previous(path)
		);
		vi.spyOn(window, 'confirm').mockReturnValue(true);
		const user = userEvent.setup();
		render(PipelineRunsView);
		await screen.findByText('Ship the feature');
		if (menu) {
			await openMenu(user);
			await user.click(menuItem(label));
		} else await user.click(screen.getByRole('button', { name: label }));

		await waitFor(() =>
			expect(api.POST).toHaveBeenCalledWith(`/api/v1/pipeline-runs/{run_id}/${action}`, {
				params: { path: { run_id: 'run-1' } },
				...(action === 'resume'
					? { body: { request_id: expect.any(String), expected_revision: 1 } }
					: {})
			})
		);
		await waitFor(() =>
			expect(api.GET.mock.calls.filter(([path]) => path === '/api/v1/pipeline-runs')).toHaveLength(
				2
			)
		);
	}
);

test('a run held by a pending question offers Answer, a marker and no plain Resume', async () => {
	const previous = api.GET.getMockImplementation()!;
	api.GET.mockImplementation((path: string) => {
		if (path === '/api/v1/pipeline-runs')
			return Promise.resolve({ data: { items: [{ ...run, state: 'paused' }], total_count: 1 } });
		if (path === '/api/v1/pipeline-runs/decisions')
			return Promise.resolve({
				data: {
					items: [
						{
							run_id: 'run-1',
							kind: 'run-question',
							question_state: 'open',
							actionable: true
						}
					],
					has_more: false,
					next_cursor: null,
					actionable_total_count: 1
				}
			});
		return previous(path);
	});
	const user = userEvent.setup();
	render(PipelineRunsView);
	await screen.findByText('Ship the feature');
	expect(screen.getByText('Question waiting')).toBeTruthy();
	expect(screen.getByRole('link', { name: 'Answer question' }).getAttribute('href')).toBe(
		'/projects/project-1/runs/run-1#decisions'
	);
	expect(screen.queryByRole('button', { name: 'Resume' })).toBeNull();
	await openMenu(user);
	const names = menuItems().map(([text]) => text);
	expect(names).not.toContain('Resume');
	expect(names).toContain('Advance now');
});

test('reads pending decisions once for the whole list, scoped to the selected project', async () => {
	render(PipelineRunsView, { scopedProject: project as never });
	await screen.findByText('Ship the feature');
	const reads = api.GET.mock.calls.filter(([path]) => path === '/api/v1/pipeline-runs/decisions');
	expect(reads).toHaveLength(1);
	expect(reads[0][1]).toEqual({
		params: { query: { project_id: 'project-1', cursor: undefined, limit: 100 } }
	});
});

test('enrolls the selected project and refreshes the run list', async () => {
	const user = userEvent.setup();
	render(PipelineRunsView);
	await screen.findByText('Ship the feature');
	await user.click(screen.getAllByRole('button', { name: 'Enroll PR' })[0]);
	await waitFor(() =>
		expect(screen.getByRole('dialog').contains(document.activeElement)).toBe(true)
	);
	await user.clear(screen.getByLabelText('Pull Request Number'));
	await user.type(screen.getByLabelText('Pull Request Number'), '42');
	await user.click(screen.getAllByRole('button', { name: 'Enroll PR' })[1]);

	await waitFor(() =>
		expect(api.POST).toHaveBeenCalledWith('/api/v1/projects/{project_id}/runs', {
			params: { path: { project_id: 'project-1' } },
			body: { pull_number: 42, implemented: false, catalog: null, handoff: false }
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

test.each([
	['/projects/runs?run=run-1', '/runs/run-1'],
	['/projects/runs?run=run-1&view=decisions', '/runs/run-1#decisions'],
	['/projects/project-1?tab=runs&run=run-1', '/runs/run-1']
])('redirects the old run deep link %s to the PR run page', async (from, to) => {
	window.history.replaceState({}, '', from);
	render(PipelineRunsView);
	await waitFor(() => expect(goto).toHaveBeenCalledWith(to, { replaceState: true }));
	expect(api.GET).not.toHaveBeenCalledWith('/api/v1/pipeline-runs', expect.anything());
	window.history.replaceState({}, '', '/projects/runs');
});

test('pages through history and resets the offset when changing state', async () => {
	const previous = api.GET.getMockImplementation()!;
	api.GET.mockImplementation(
		async (path: string, options?: { params: { query: { offset?: number } } }) => {
			if (path !== '/api/v1/pipeline-runs') return previous(path, options);
			return {
				data: {
					items: [
						{
							...run,
							pull_snapshot: {
								title: options?.params.query.offset ? 'Old run' : 'Ship the feature'
							}
						}
					],
					total_count: 51
				}
			};
		}
	);
	const user = userEvent.setup();
	render(PipelineRunsView);
	await screen.findByText('Ship the feature');
	await user.click(screen.getByRole('button', { name: 'Next page' }));
	expect(await screen.findByText('Old run')).toBeTruthy();
	await user.selectOptions(screen.getByRole('combobox', { name: 'Run state' }), 'blocked');
	await waitFor(() =>
		expect(api.GET).toHaveBeenCalledWith('/api/v1/pipeline-runs', {
			params: {
				query: { search: '', state: 'blocked', project_id: undefined, offset: 0, limit: 50 }
			}
		})
	);
});

test('attaches a PR to the selected run and refreshes the list', async () => {
	const previous = api.GET.getMockImplementation()!;
	api.GET.mockImplementation((path: string) =>
		path === '/api/v1/pipeline-runs'
			? Promise.resolve({
					data: { items: [{ ...run, pull_number: 0, pull_url: null }], total_count: 1 }
				})
			: previous(path)
	);
	const user = userEvent.setup();
	render(PipelineRunsView);
	await screen.findByText('Ship the feature');
	await user.click(screen.getByRole('button', { name: 'Attach PR' }));
	await waitFor(() =>
		expect(screen.getByRole('dialog').contains(document.activeElement)).toBe(true)
	);
	await user.clear(screen.getByLabelText('Pull Request Number'));
	await user.type(screen.getByLabelText('Pull Request Number'), '12');
	await user.clear(screen.getByLabelText('Pull Request URL (optional)'));
	await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Attach PR' }));
	await waitFor(() =>
		expect(api.POST).toHaveBeenCalledWith('/api/v1/pipeline-runs/{run_id}/attach-pr', {
			params: { path: { run_id: 'run-1' } },
			body: { pull_number: 12, pull_url: null }
		})
	);
	await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
	expect(api.GET.mock.calls.filter(([path]) => path === '/api/v1/pipeline-runs')).toHaveLength(2);
});
