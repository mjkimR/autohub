import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { toast } from 'svelte-sonner';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import ProjectsView from './ProjectsView.svelte';

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
