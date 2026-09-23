import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import ProjectDetailView from './ProjectDetailView.svelte';
import ConnectionTestsPanel from './ConnectionTestsPanel.svelte';
import type { components } from '$lib/api';
import { projectTab } from './project-tabs';

const { api } = vi.hoisted(() => ({
	api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() }
}));
vi.mock('$lib/api', () => ({ api }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn(), success: vi.fn(), warning: vi.fn() } }));

const project = {
	id: 'p1',
	name: 'Application',
	enabled: true,
	revision: 4,
	github: {
		repository: 'owner/app',
		github_connector_id: 'c1',
		ai_catalog_id: null,
		template_id: 'python-uv',
		verification: { workflow: 'ci.yml', required_jobs: ['test'], event: 'pull_request' },
		automation: {
			auto_merge: true,
			merge_method: 'squash',
			auto_fix_ci: true,
			auto_fix_conflicts: false,
			auto_enroll_on_trigger: true,
			auto_enroll_sessions: true,
			dispatch_interval_seconds: 120,
			max_in_flight_runs: 2
		}
	},
	last_check: null,
	template_version: '1',
	created_at: '2026-09-22T00:00:00Z',
	updated_at: '2026-09-22T00:00:00Z'
} satisfies components['schemas']['ProjectRead'];
const catalogs = [
	{
		id: 'codex',
		key: 'personal-codex',
		name: 'Personal Codex',
		kind: 'codex',
		enabled: true,
		connection_test: true,
		adapter: 'codex-github-mention',
		connector_id: null
	},
	{
		id: 'jules',
		key: 'personal-jules',
		name: 'Personal Jules',
		kind: 'jules',
		enabled: true,
		connection_test: true,
		adapter: 'jules-api',
		connector_id: 'jc1'
	}
] as components['schemas']['AICatalogRead'][];
const testOptions = catalogs.map((catalog) => ({
	ai_catalog_id: catalog.id,
	name: catalog.name,
	kind: catalog.kind,
	ready: true,
	configuration_fingerprint: 'config-v1',
	requirements: [],
	spec: {
		key: catalog.adapter,
		version: 1,
		create_once: catalog.kind === 'jules',
		discovers_output_pr: catalog.kind === 'jules',
		manual_cleanup_resolution: catalog.kind === 'jules',
		title: `${catalog.name} recipe`,
		description: `${catalog.name} instructions`,
		delivery_key: 'request',
		requirements: [],
		phases: { preparing: 'Checking access and preparing test branch' },
		evidence: [
			{ key: 'pull_url', label: 'Test PR', origin: 'https://github.com' },
			{ key: 'session_state', label: 'Session', origin: null },
			{ key: 'session_url', label: 'Jules session', origin: 'https://jules.google.com' }
		]
	}
})) satisfies components['schemas']['ConnectionTestOption'][];
const probe = {
	id: 't1',
	project_id: 'p1',
	project_revision: 4,
	configuration_current: true,
	test_spec: testOptions[0].spec,
	repository: 'owner/app',
	status: 'succeeded',
	phase: 'verified',
	cleanup_status: 'failed',
	detail: 'Test change was pushed and required CI passed',
	cancel_requested: false,
	evidence: {
		verified_sha: 'abc',
		ci_status: 'passed',
		cleanup_error: 'GitHub unavailable',
		pull_url: 'https://github.com/owner/app/pull/42'
	},
	created_at: '2026-09-22T00:00:00Z',
	deadline: '2026-09-22T01:00:00Z',
	finished_at: '2026-09-22T00:05:00Z'
};
beforeEach(() => {
	api.GET.mockImplementation(async (path: string) => {
		if (path === '/api/v1/ai-catalogs') return { data: { items: catalogs } };
		if (path === '/api/v1/projects/{project_id}') return { data: project };
		if (path.endsWith('/connection-tests/options')) return { data: testOptions };
		if (path.endsWith('/connection-tests')) return { data: [] };
		if (path === '/api/v1/connectors')
			return {
				data: {
					items: [{ id: 'c1', name: 'GitHub', provider: 'github', enabled: true }],
					total_count: 1
				}
			};
		return { data: { items: [], total_count: 0 } };
	});
	api.PATCH.mockResolvedValue({ data: project });
});
afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

test('detail exposes bookmarkable tabs and opens project-scoped runs', async () => {
	const view = render(ProjectDetailView, { projectId: 'p1', tab: 'overview' });
	expect(await screen.findByRole('heading', { name: 'Application' })).toBeTruthy();
	expect(screen.getByRole('link', { name: 'Connections' }).getAttribute('href')).toBe(
		'/projects/p1?tab=connections'
	);
	expect(screen.getByRole('link', { name: 'Overview' }).getAttribute('aria-current')).toBe('page');
	await view.rerender({ projectId: 'p1', tab: 'runs' });
	await screen.findByRole('heading', { name: 'Pipeline Runs' });
	await waitFor(() =>
		expect(api.GET).toHaveBeenCalledWith(
			'/api/v1/pipeline-runs',
			expect.objectContaining({ params: { query: expect.objectContaining({ project_id: 'p1' }) } })
		)
	);
	expect(
		(screen.getByRole('combobox', { name: 'Project filter' }) as HTMLSelectElement).disabled
	).toBe(true);
});

test('settings edit preserves connection, template and automatic merge policy', async () => {
	const user = userEvent.setup();
	render(ProjectDetailView, { projectId: 'p1', tab: 'settings' });
	const name = await screen.findByLabelText('Project Name');
	await fireEvent.input(name, { target: { value: 'Renamed' } });
	await user.click(screen.getByRole('button', { name: 'Save Changes' }));
	await waitFor(() =>
		expect(api.PATCH).toHaveBeenCalledWith(
			'/api/v1/projects/{project_id}',
			expect.objectContaining({
				body: expect.objectContaining({
					name: 'Renamed',
					expected_revision: 4,
					github: project.github
				})
			})
		)
	);
	expect(screen.queryByLabelText('Repository (owner/repo)')).toBeNull();
});

test('connection history survives remount and separates verification from cleanup', async () => {
	const previous = api.GET.getMockImplementation()!;
	api.GET.mockImplementation((path: string, options: unknown) =>
		path.endsWith('/connection-tests')
			? Promise.resolve({ data: [probe] })
			: previous(path, options)
	);
	const view = render(ConnectionTestsPanel, { project, catalogs });
	expect(await screen.findByText('Legacy Codex · Verified')).toBeTruthy();
	expect(screen.getByText('Cleanup: failed')).toBeTruthy();
	expect(screen.getByRole('link', { name: 'Test PR' }).getAttribute('href')).toBe(
		probe.evidence.pull_url
	);
	view.unmount();
	api.GET.mockImplementation((path: string) =>
		Promise.resolve({
			data: path.endsWith('/options') ? testOptions : [{ ...probe, configuration_current: false }]
		})
	);
	render(ConnectionTestsPanel, { project: { ...project, revision: 5 }, catalogs });
	expect(await screen.findByText('Configuration changed — retest recommended')).toBeTruthy();
	expect(api.POST).not.toHaveBeenCalled();
});

test('an ambiguous start retries the same request ID and disables another test while active', async () => {
	const user = userEvent.setup();
	const running = {
		...probe,
		status: 'running',
		phase: 'preparing',
		cleanup_status: 'pending',
		evidence: {}
	};
	api.POST.mockRejectedValueOnce(new Error('response lost')).mockResolvedValueOnce({
		data: running
	});
	render(ConnectionTestsPanel, { project, catalogs });
	await waitFor(() =>
		expect(
			(screen.getByRole('button', { name: 'Start PR test' }) as HTMLButtonElement).disabled
		).toBe(false)
	);
	await user.click(screen.getByRole('button', { name: 'Start PR test' }));
	await waitFor(() =>
		expect(
			(screen.getByRole('button', { name: 'Start PR test' }) as HTMLButtonElement).disabled
		).toBe(false)
	);
	api.GET.mockImplementation(async (path: string) => ({
		data: path.endsWith('/options') ? testOptions : [running]
	}));
	await user.click(screen.getByRole('button', { name: 'Start PR test' }));
	await screen.findByText('Checking access and preparing test branch');
	expect(api.POST.mock.calls[0][1].body.request_id).toBe(api.POST.mock.calls[1][1].body.request_id);
	expect(
		(screen.getByRole('button', { name: 'Start PR test' }) as HTMLButtonElement).disabled
	).toBe(true);
});

test('unknown tab falls back to overview', () => {
	expect(projectTab('missing')).toBe('overview');
	expect(projectTab('connections')).toBe('connections');
});

test('Jules selection posts its catalog ID and shows session evidence separately from Codex', async () => {
	const user = userEvent.setup();
	render(ConnectionTestsPanel, { project, catalogs });
	await screen.findByRole('option', { name: /Personal Jules · jules/ });
	await user.selectOptions(screen.getByLabelText('Test AI catalog'), 'jules');
	api.POST.mockResolvedValue({ data: probe });
	await user.click(screen.getByRole('button', { name: 'Start PR test' }));
	await waitFor(() =>
		expect(api.POST).toHaveBeenCalledWith(
			'/api/v1/projects/{project_id}/connection-tests',
			expect.objectContaining({
				body: expect.objectContaining({ ai_catalog_id: 'jules' })
			})
		)
	);
	cleanup();
	api.GET.mockImplementation(async (path: string) => ({
		data: path.endsWith('/options')
			? testOptions
			: [
					{
						...probe,
						ai_catalog_id: 'jules',
						catalog_snapshot: catalogs[1],
						evidence: {
							session_state: 'completed',
							session_url: 'https://jules.google.com/session/123',
							ci_status: 'passed'
						}
					}
				]
	}));
	render(ConnectionTestsPanel, { project, catalogs });
	expect(await screen.findByText('Personal Jules · Verified')).toBeTruthy();
	expect(screen.getByText('Session: completed')).toBeTruthy();
	expect(screen.getByRole('link', { name: 'Jules session' }).getAttribute('href')).toBe(
		'https://jules.google.com/session/123'
	);
	expect(screen.queryByText('Codex response: not observed')).toBeNull();
});

test('a new recipe renders its own prerequisites without a provider-specific UI branch', async () => {
	const option = {
		...testOptions[0],
		ai_catalog_id: 'new-provider',
		kind: 'new-provider',
		name: 'New Provider',
		ready: false,
		requirements: [{ key: 'workspace', status: 'missing' }],
		spec: {
			...testOptions[0].spec,
			title: 'Workspace probe',
			description: 'Checks a provider workspace',
			requirements: [
				{
					key: 'workspace',
					label: 'Workspace credential',
					source: 'catalog_connector',
					description: 'Assign a workspace credential before testing.'
				}
			]
		}
	};
	api.GET.mockImplementation(async (path: string) => ({
		data: path.endsWith('/options') ? [option] : []
	}));
	render(ConnectionTestsPanel, { project, catalogs });
	expect(await screen.findByText('Workspace probe')).toBeTruthy();
	expect(screen.getByText('Assign a workspace credential before testing.')).toBeTruthy();
	expect(
		(screen.getByRole('button', { name: 'Start PR test' }) as HTMLButtonElement).disabled
	).toBe(true);
	expect(screen.queryByText('Personal Codex instructions')).toBeNull();
});
