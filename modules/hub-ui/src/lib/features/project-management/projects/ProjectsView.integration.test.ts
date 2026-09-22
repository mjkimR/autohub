import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { toast } from 'svelte-sonner';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import ProjectsView from './ProjectsView.svelte';

const { api } = vi.hoisted(() => ({
	api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() }
}));

vi.mock('$lib/api', () => ({ api }));
vi.mock('svelte-sonner', () => ({
	toast: { error: vi.fn(), success: vi.fn(), warning: vi.fn() }
}));

const project = {
	id: 'p1',
	name: 'Application',
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
	api.PUT.mockResolvedValue({ data: project });
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
			body: { name: 'backend-pipeline', enabled: true }
		})
	);
});

test('an edit sends the revision it started from and keeps the automation it did not touch', async () => {
	const user = userEvent.setup();
	render(ProjectsView);
	await screen.findByText('Application');

	await user.click(screen.getByText('Quick actions'));
	await user.click(screen.getByRole('button', { name: 'Configure Project' }));
	// The limit is empty for "no project limit"; a number caps the project's runs in flight.
	const limit = document.getElementById('maxInFlightRuns') as HTMLInputElement;
	expect(limit.value).toBe('');
	await fireEvent.input(limit, { target: { value: '2' } });
	await user.click(screen.getByRole('button', { name: 'Save Changes' }));

	await waitFor(() => expect(api.PUT).toHaveBeenCalledTimes(1));
	const [path, request] = api.PUT.mock.calls[0];
	expect(path).toBe('/api/v1/projects/{project_id}');
	expect(request.params).toEqual({ path: { project_id: 'p1' } });
	expect(request.body).toMatchObject({ name: 'Application', enabled: true, expected_revision: 4 });
	expect(request.body.github.verification.required_jobs).toEqual(['lint', 'test']);
	expect(request.body.github.automation).toEqual({
		...project.github.automation,
		max_in_flight_runs: 2
	});
});

test('a connection check reports what the backend found', async () => {
	api.POST.mockResolvedValue({ error: { detail: 'GitHub observation returned HTTP 401' } });
	const user = userEvent.setup();
	render(ProjectsView);
	await screen.findByText('Application');

	await user.click(screen.getByText('Quick actions'));
	await user.click(screen.getByRole('button', { name: 'Connection Check' }));
	await user.click(screen.getByRole('button', { name: 'Run Check' }));

	await waitFor(() =>
		expect(toast.error).toHaveBeenCalledWith('GitHub observation returned HTTP 401')
	);
	expect(api.POST.mock.calls[0][0]).toBe('/api/v1/projects/{project_id}/check');
});

test('an invalid edit shows validation messages and keeps the dialog open', async () => {
	api.PUT.mockResolvedValue({ error: { detail: [{ msg: 'Dispatch interval must be positive' }] } });
	const user = userEvent.setup();
	render(ProjectsView);
	await screen.findByText('Application');
	await user.click(screen.getByText('Quick actions'));
	await user.click(screen.getByRole('button', { name: 'Configure Project' }));
	await user.click(screen.getByRole('button', { name: 'Save Changes' }));

	await waitFor(() =>
		expect(toast.error).toHaveBeenCalledWith('Dispatch interval must be positive')
	);
	expect(screen.getByRole('button', { name: 'Save Changes' })).toBeTruthy();
	await waitFor(() =>
		expect(
			(screen.getByRole('button', { name: 'Save Changes' }) as HTMLButtonElement).disabled
		).toBe(false)
	);
});

test('a delete asks first and explains a refusal', async () => {
	vi.stubGlobal('confirm', vi.fn().mockReturnValueOnce(false).mockReturnValue(true));
	api.DELETE.mockResolvedValue({ error: { detail: 'Project still has pipeline runs' } });
	const user = userEvent.setup();
	render(ProjectsView);
	await screen.findByText('Application');

	await user.click(screen.getByText('Quick actions'));
	await user.click(screen.getByRole('button', { name: 'Delete Project' }));
	expect(api.DELETE).not.toHaveBeenCalled();

	await user.click(screen.getByText('Quick actions'));
	await user.click(screen.getByRole('button', { name: 'Delete Project' }));
	await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Project still has pipeline runs'));
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

test('quick schedules keep the selected project and reset the form after closing', async () => {
	const user = userEvent.setup();
	render(ProjectsView);
	await screen.findByText('Application');
	await user.click(screen.getByText('Quick actions'));
	await user.click(screen.getByRole('button', { name: 'Create Schedule' }));
	await user.click(screen.getByRole('button', { name: /Observe CI/ }));
	await fireEvent.input(screen.getByLabelText('Pull Request Numbers (comma-separated)'), {
		target: { value: '42, 105' }
	});
	await user.click(
		within(screen.getByRole('dialog')).getByRole('button', { name: 'Create Schedule' })
	);
	await waitFor(() =>
		expect(api.POST).toHaveBeenCalledWith('/api/v1/schedule_configs', {
			body: {
				name: 'Observe Application',
				description: 'CI observation for Application',
				task_func: 'pipeline.observe_project',
				cron_expression: null,
				interval_seconds: 300,
				payload: { project_id: 'p1', pull_numbers: [42, 105] },
				enabled: true
			}
		})
	);
	await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
	await waitFor(() => expect(getComputedStyle(document.body).pointerEvents).not.toBe('none'));
	await user.click(screen.getByText('Quick actions'));
	await user.click(screen.getByRole('button', { name: 'Create Schedule' }));
	expect(screen.queryByLabelText('Pull Request Numbers (comma-separated)')).toBeNull();
	expect(screen.getByDisplayValue('Dispatch Application')).toBeTruthy();
});
