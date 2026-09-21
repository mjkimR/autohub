import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
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

	await user.click(screen.getByRole('button', { name: 'Connection Check' }));
	await user.click(screen.getByRole('button', { name: 'Run Check' }));

	await waitFor(() =>
		expect(toast.error).toHaveBeenCalledWith('GitHub observation returned HTTP 401')
	);
	expect(api.POST.mock.calls[0][0]).toBe('/api/v1/projects/{project_id}/check');
});

test('a delete asks first and explains a refusal', async () => {
	vi.stubGlobal('confirm', vi.fn().mockReturnValueOnce(false).mockReturnValue(true));
	api.DELETE.mockResolvedValue({ error: { detail: 'Project still has pipeline runs' } });
	const user = userEvent.setup();
	render(ProjectsView);
	await screen.findByText('Application');

	await user.click(screen.getByRole('button', { name: 'Delete Project' }));
	expect(api.DELETE).not.toHaveBeenCalled();

	await user.click(screen.getByRole('button', { name: 'Delete Project' }));
	await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Project still has pipeline runs'));
});
