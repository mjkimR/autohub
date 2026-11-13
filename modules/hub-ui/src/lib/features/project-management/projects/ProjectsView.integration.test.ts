import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { toast } from 'svelte-sonner';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import ProjectsView from './ProjectsView.svelte';
import { OWED_COUNTS_CONTEXT, OwedCountsStore } from '$lib/features/attention/owed-counts.svelte';

const { api } = vi.hoisted(() => ({
	api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() }
}));

vi.mock('$lib/api', () => ({ api }));
vi.mock('svelte-sonner', () => ({
	toast: { error: vi.fn(), success: vi.fn(), warning: vi.fn() }
}));

const project = {
	id: 'p1',
	name: 'Application',
	project_type: 'general',
	enabled: true,
	revision: 4,
	github: {
		repository: 'owner/app',
		github_connector_id: 'c1',
		ai_catalog_id: null,
		template_id: null,
		verification: { workflow: 'ci.yml', required_jobs: ['lint', 'test'], event: 'pull_request' },
		automation: {
			auto_merge: true,
			repository_viewer: 'default',
			merge_method: 'squash',
			auto_fix_ci: true,
			auto_fix_conflicts: false,
			auto_enroll_on_trigger: true,
			auto_enroll_sessions: true,
			dispatch_interval_seconds: 120,
			max_in_flight_runs: null
		}
	},
	last_check: null,
	created_at: '2026-09-21T00:00:00Z',
	updated_at: '2026-09-21T00:00:00Z'
};

beforeEach(() => {
	api.GET.mockImplementation(async (path: string) => {
		if (path === '/api/v1/connectors')
			return {
				data: { items: [{ id: 'c1', name: 'Org PAT', provider: 'github', enabled: true }] }
			};
		if (path === '/api/v1/ai-catalogs') return { data: { items: [] } };
		return { data: { items: [project], total_count: 1 } };
	});
	api.POST.mockResolvedValue({ data: project });
	api.PATCH.mockResolvedValue({ data: project });
	api.DELETE.mockResolvedValue({ data: {} });
});

afterEach(() => {
	cleanup();
	document.body.style.removeProperty('pointer-events');
	vi.clearAllMocks();
	vi.unstubAllGlobals();
});

test('registers a project by name', async () => {
	const user = userEvent.setup();
	render(ProjectsView);
	expect(await screen.findByText('Application')).toBeTruthy();

	await user.click(screen.getByRole('button', { name: /New Project/ }));
	await fireEvent.input(document.getElementById('pName') as HTMLInputElement, {
		target: { value: ' backend-pipeline ' }
	});
	await user.click(screen.getByRole('button', { name: 'Create Project' }));

	await waitFor(() =>
		expect(api.POST).toHaveBeenCalledWith('/api/v1/projects', {
			body: { name: 'backend-pipeline', project_type: 'general', enabled: true }
		})
	);
});

test('rows link into the project Setup tabs instead of a second edit dialog', async () => {
	render(ProjectsView);
	await screen.findByText('Application');

	expect(
		screen.getByRole('link', { name: 'Automation for Application' }).getAttribute('href')
	).toBe('/projects/p1?tab=automation');
	expect(screen.getByRole('link', { name: 'Settings for Application' }).getAttribute('href')).toBe(
		'/projects/p1?tab=settings'
	);
	expect(screen.queryByText('Quick actions')).toBeNull();
	expect(screen.queryByRole('button', { name: 'Configure Project' })).toBeNull();
	expect(screen.queryByRole('button', { name: 'Create Schedule' })).toBeNull();
	expect(screen.queryByRole('button', { name: 'Agent Schedules' })).toBeNull();
	expect(screen.queryByRole('button', { name: 'Delete Project' })).toBeNull();
	// The list no longer loads the connector and catalog options only those dialogs needed.
	expect(api.GET).not.toHaveBeenCalledWith('/api/v1/connectors', expect.anything());
});

test('a connection check reports what the backend found', async () => {
	api.POST.mockResolvedValue({ error: { detail: 'GitHub observation returned HTTP 401' } });
	const user = userEvent.setup();
	render(ProjectsView);
	await screen.findByText('Application');

	// An unchecked project still opens its GitHub access check from the list.
	expect(screen.getByText('Unchecked')).toBeTruthy();
	await user.click(
		screen.getByRole('button', { name: 'Open GitHub access check for Application' })
	);
	await user.click(screen.getByRole('button', { name: 'Run Check' }));

	await waitFor(() =>
		expect(toast.error).toHaveBeenCalledWith('GitHub observation returned HTTP 401')
	);
	expect(api.POST.mock.calls[0][0]).toBe('/api/v1/projects/{project_id}/check');
});

test('pages past 50 projects and sends search to the server from the first page', async () => {
	const previous = api.GET.getMockImplementation()!;
	api.GET.mockImplementation(
		async (path: string, options?: { params: { query: { offset: number; search?: string } } }) => {
			if (path !== '/api/v1/projects') return previous(path, options);
			const query = options!.params.query;
			return {
				data: {
					items: [
						{
							...project,
							id: query.offset ? 'p51' : 'p1',
							name: query.offset ? 'Last project' : 'Application'
						}
					],
					total_count: query.search ? 1 : 51
				}
			};
		}
	);
	const user = userEvent.setup();
	render(ProjectsView);
	await screen.findByText('Application');
	await user.click(screen.getByRole('button', { name: 'Next page' }));
	expect(await screen.findByText('Last project')).toBeTruthy();
	await fireEvent.input(screen.getByPlaceholderText('Search projects or repositories...'), {
		target: { value: 'older' }
	});
	await waitFor(() =>
		expect(api.GET).toHaveBeenCalledWith('/api/v1/projects', {
			params: { query: { search: 'older', offset: 0, limit: 50 } }
		})
	);
});

test('an HTTP list failure is distinct from no projects and can be retried', async () => {
	api.GET.mockResolvedValue({ error: { detail: 'Unavailable' } });
	const user = userEvent.setup();
	render(ProjectsView);
	await screen.findByRole('alert');
	expect(screen.queryByText('No projects found')).toBeNull();
	api.GET.mockResolvedValue({ data: { items: [project], total_count: 1 } });
	await user.click(screen.getByRole('button', { name: 'Retry' }));
	expect(await screen.findByText('Application')).toBeTruthy();
	expect(screen.queryByRole('alert')).toBeNull();
});

function countsCalls() {
	return api.GET.mock.calls.filter(([path]) => path === '/api/v1/owed-items/counts');
}
function withCounts(result: () => Promise<{ data?: unknown; error?: unknown }>) {
	const previous = api.GET.getMockImplementation()!;
	api.GET.mockImplementation(async (path: string, options?: unknown) =>
		path === '/api/v1/owed-items/counts' ? result() : previous(path, options)
	);
}
const other = { ...project, id: 'p2', name: 'Library' };
function twoProjects() {
	const previous = api.GET.getMockImplementation()!;
	api.GET.mockImplementation(async (path: string, options?: unknown) =>
		path === '/api/v1/projects'
			? { data: { items: [project, other], total_count: 2 } }
			: previous(path, options)
	);
}

test('outside the shell, Needs you falls back to one local counts read per load', async () => {
	twoProjects();
	withCounts(async () => ({ data: { total: 3, by_kind: {}, by_project: { p1: 3 } } }));
	const user = userEvent.setup();
	render(ProjectsView);
	expect(screen.getByRole('columnheader', { name: 'Needs you' })).toBeTruthy();
	// The column and the narrow-layout copy under the name carry the same link.
	const links = await screen.findAllByRole('link', { name: 'Application: 3 items need you' });
	expect(links).toHaveLength(2);
	const counted = links[0];
	expect(counted.getAttribute('href')).toBe('/projects/p1?tab=overview#needs-you');
	expect(counted.className).toContain('attention');
	// A project with nothing owed shows nothing: no zero, no dash.
	const libraryRow = screen.getByText('Library').closest('tr') as HTMLElement;
	expect(libraryRow.querySelector('[data-owed-count]')).toBeNull();
	expect(libraryRow.querySelector('[data-owed-unknown]')).toBeNull();
	// Never a full-row fill.
	expect(libraryRow.className).not.toContain('attention');
	expect((counted.closest('tr') as HTMLElement).className).not.toContain('attention');
	expect(countsCalls()).toHaveLength(1);
	expect(countsCalls()[0]).toEqual(['/api/v1/owed-items/counts']);

	// Search and paging reuse the counts; Refresh reads them once more.
	await fireEvent.input(screen.getByPlaceholderText('Search projects or repositories...'), {
		target: { value: 'app' }
	});
	await waitFor(() => expect(api.GET).toHaveBeenCalledTimes(3));
	expect(countsCalls()).toHaveLength(1);
	await user.click(screen.getByRole('button', { name: /Refresh/ }));
	await waitFor(() => expect(countsCalls()).toHaveLength(2));
});

test('Needs you stays a neutral dash while counts are unknown', async () => {
	withCounts(() => new Promise(() => {}));
	render(ProjectsView);
	const row = (await screen.findByText('Application')).closest('tr') as HTMLElement;
	expect(row.querySelector('[data-owed-unknown]')?.textContent).toContain('—');
	expect(row.querySelector('[data-owed-count]')).toBeNull();
});

test('a failed counts read is a dash with the reason, not zero', async () => {
	withCounts(async () => ({ error: { detail: 'Database busy' } }));
	render(ProjectsView);
	await screen.findByText('Application');
	await waitFor(() =>
		expect(
			(document.querySelector('[data-owed-unknown][title]') as HTMLElement | null)?.title
		).toBe('Needs-you count unavailable: Database busy')
	);
	expect(document.querySelector('[data-owed-count]')).toBeNull();
	// The list itself still loads.
	expect(screen.queryByRole('alert')).toBeNull();
});

test('inside the shell, Needs you reuses the shared counts store without its own read', async () => {
	twoProjects();
	withCounts(async () => ({ data: { total: 2, by_kind: {}, by_project: { p2: 2 } } }));
	const store = new OwedCountsStore();
	store.value = { status: 'known', total: 3, byKind: {}, byProject: { p1: 3 } };
	const user = userEvent.setup();
	render(ProjectsView, { context: new Map([[OWED_COUNTS_CONTEXT, store]]) });
	const links = await screen.findAllByRole('link', { name: 'Application: 3 items need you' });
	expect(links).toHaveLength(2);
	// The shell already read the counts; mounting the list adds no duplicate request.
	expect(countsCalls()).toHaveLength(0);

	// Refresh goes through the shared store, so the shell badge moves with the list.
	await user.click(screen.getByRole('button', { name: /Refresh/ }));
	await waitFor(() => expect(countsCalls()).toHaveLength(1));
	expect(await screen.findAllByRole('link', { name: 'Library: 2 items need you' })).toHaveLength(2);
	expect(store.value).toMatchObject({ status: 'known', total: 2 });
	expect(screen.queryByRole('link', { name: 'Application: 3 items need you' })).toBeNull();
});

test('inside the shell, an unknown shared count stays a neutral dash', async () => {
	const store = new OwedCountsStore();
	render(ProjectsView, { context: new Map([[OWED_COUNTS_CONTEXT, store]]) });
	const row = (await screen.findByText('Application')).closest('tr') as HTMLElement;
	expect(row.querySelector('[data-owed-unknown]')?.textContent).toContain('—');
	expect(row.querySelector('[data-owed-count]')).toBeNull();
	expect(countsCalls()).toHaveLength(0);
});

test('a shared counts failure keeps the reason in both neutral tooltip copies without another read', async () => {
	withCounts(async () => ({ error: { detail: 'Database busy' } }));
	const store = new OwedCountsStore();
	await store.refresh();
	render(ProjectsView, { context: new Map([[OWED_COUNTS_CONTEXT, store]]) });
	await screen.findByText('Application');
	const unknowns = document.querySelectorAll('[data-owed-unknown]');
	expect(unknowns).toHaveLength(2);
	for (const mark of unknowns) {
		expect(mark.getAttribute('title')).toBe('Needs-you count unavailable: Database busy');
		expect(mark.textContent).toContain('—');
	}
	expect(document.querySelector('[data-owed-count]')).toBeNull();
	expect(countsCalls()).toHaveLength(1);
});
