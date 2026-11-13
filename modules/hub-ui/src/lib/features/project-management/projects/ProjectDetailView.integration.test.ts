import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import ProjectDetailView from './ProjectDetailView.svelte';
import ProjectSettingsForm from './ProjectSettingsForm.svelte';
import ConnectionTestsPanel from './ConnectionTestsPanel.svelte';
import type { components } from '$lib/api';
import { projectTab, projectTabGroups } from './project-tabs';
import { toast } from 'svelte-sonner';

const { api } = vi.hoisted(() => ({
	api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() }
}));
vi.mock('$lib/api', () => ({ api }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn(), success: vi.fn(), warning: vi.fn() } }));

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
		template_id: 'python-uv',
		verification: { workflow: 'ci.yml', required_jobs: ['test'], event: 'pull_request' },
		automation: {
			auto_merge: true,
			repository_viewer: 'default',
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
	document.body.style.removeProperty('pointer-events');
	vi.clearAllMocks();
	vi.unstubAllGlobals();
});

test('detail exposes bookmarkable tabs and opens project-scoped runs', async () => {
	const view = render(ProjectDetailView, { projectId: 'p1', tab: 'overview' });
	expect(await screen.findByRole('heading', { name: 'Application' })).toBeTruthy();
	expect(screen.getByRole('link', { name: 'Connections' }).getAttribute('href')).toBe(
		'/projects/p1?tab=connections'
	);
	expect(screen.getByRole('link', { name: 'Overview' }).getAttribute('aria-current')).toBe('page');
	await view.rerender({ projectId: 'p1', tab: 'runs' });
	await screen.findByRole('heading', { name: 'PR runs' });
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

test('unknown tab falls back to overview and every grouped tab keeps its query value', () => {
	expect(projectTab('missing')).toBe('overview');
	for (const id of [
		'overview',
		'repository',
		'runs',
		'plans',
		'connections',
		'automation',
		'settings'
	])
		expect(projectTab(id)).toBe(id);
	expect(projectTabGroups.map((group) => group.tabs.map((tab) => tab.id))).toEqual([
		['overview', 'runs', 'plans', 'repository'],
		['connections', 'automation', 'settings']
	]);
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

test('general settings save project_type successfully', async () => {
	const user = userEvent.setup();
	render(ProjectSettingsForm, {
		project,
		connectors: [],
		catalogs: [],
		section: 'general',
		onsaved: vi.fn()
	});
	await user.selectOptions(screen.getByRole('combobox', { name: 'Project Type' }), 'sdd');
	await user.click(screen.getByRole('button', { name: 'Save Changes' }));
	expect(api.PATCH).toHaveBeenCalledWith(
		'/api/v1/projects/{project_id}',
		expect.objectContaining({
			body: expect.objectContaining({
				project_type: 'sdd'
			})
		})
	);
});

test('sections are grouped into Work and Setup and the breadcrumb names the project', async () => {
	render(ProjectDetailView, { projectId: 'p1', tab: 'automation' });
	await screen.findByRole('heading', { name: 'Application', level: 1 });

	const breadcrumb = screen.getByRole('navigation', { name: 'Breadcrumb' });
	expect(within(breadcrumb).getByRole('link', { name: 'Projects' }).getAttribute('href')).toBe(
		'/projects'
	);
	expect(within(breadcrumb).getByText('Application').getAttribute('aria-current')).toBe('page');

	const sections = screen.getByRole('navigation', { name: 'Project sections' });
	const links = (name: string) =>
		within(within(sections).getByRole('group', { name })).getAllByRole('link');
	expect(links('Work').map((link) => [link.textContent, link.getAttribute('href')])).toEqual([
		['Overview', '/projects/p1?tab=overview'],
		['Runs', '/projects/p1?tab=runs'],
		['Plans', '/projects/p1?tab=plans'],
		['Repository', '/projects/p1?tab=repository']
	]);
	expect(links('Setup').map((link) => [link.textContent, link.getAttribute('href')])).toEqual([
		['Connections', '/projects/p1?tab=connections'],
		['Automation', '/projects/p1?tab=automation'],
		['Settings', '/projects/p1?tab=settings']
	]);
	expect(
		within(sections)
			.getAllByRole('link')
			.filter((link) => link.getAttribute('aria-current') === 'page')
			.map((link) => link.textContent)
	).toEqual(['Automation']);
});

const scheduleConfig = (id: string, name: string, task_func: string, payload: object) => ({
	id,
	name,
	description: null,
	task_func,
	cron_expression: null,
	interval_seconds: 300,
	payload,
	enabled: true,
	next_run_at: '2026-09-22T00:10:00Z',
	last_run_at: null,
	created_at: '2026-09-21T00:00:00Z',
	updated_at: '2026-09-21T00:00:00Z'
});

function mockOwnedSchedules() {
	const previous = api.GET.getMockImplementation()!;
	const configs = [
		scheduleConfig('d1', 'Dispatch Application', 'pipeline.dispatch_project', {
			project_id: 'p1'
		}),
		scheduleConfig('d2', 'Dispatch Other', 'pipeline.dispatch_project', { project_id: 'p2' }),
		scheduleConfig('o1', 'Observe Application', 'pipeline.observe_project', {
			project_id: 'p1',
			pull_numbers: [42, 105]
		}),
		scheduleConfig('o2', 'Observe Other', 'pipeline.observe_project', {
			project_id: 'p2',
			pull_numbers: [1]
		}),
		scheduleConfig('t1', 'Legacy probe', 'pipeline.connection_test', { test_id: 't1' }),
		scheduleConfig('t2', 'Other probe', 'pipeline.connection_test', { test_id: 'other' })
	];
	api.GET.mockImplementation(
		(path: string, options?: { params?: { query?: { task_func?: string } } }) => {
			if (path === '/api/v1/schedule_configs') {
				const task = options?.params?.query?.task_func ?? '';
				const items = configs.filter((config) => config.task_func.includes(task));
				return Promise.resolve({ data: { items, total_count: items.length } });
			}
			if (path === '/api/v1/projects/{project_id}/connection-tests')
				return Promise.resolve({ data: [probe] });
			if (path === '/api/v1/projects/{project_id}/agent-schedules')
				return Promise.resolve({
					data: {
						items: [
							{
								id: 'as1',
								project_id: 'p1',
								schedule_config_id: 'cfg-as1',
								ai_catalog_id: 'jules',
								work_type: 'task',
								title: 'Weekly hygiene',
								prompt: 'Tidy up.',
								starting_branch: 'main',
								enabled: true,
								cron_expression: '0 9 * * 1',
								interval_seconds: null,
								task_func: 'jules.session',
								next_run_at: null,
								last_run_at: null,
								recent_sessions: [],
								created_at: '2026-09-10T00:00:00Z',
								updated_at: '2026-09-10T00:00:00Z'
							}
						]
					}
				});
			return previous(path, options);
		}
	);
}

test('automation shows every schedule the project owns and nothing another project owns', async () => {
	mockOwnedSchedules();
	render(ProjectDetailView, { projectId: 'p1', tab: 'automation' });

	expect(await screen.findByText('Dispatch Application')).toBeTruthy();
	expect(screen.getByText('Observe Application')).toBeTruthy();
	expect(screen.getByText('PR #42, PR #105')).toBeTruthy();
	expect(screen.getByText('Legacy probe')).toBeTruthy();
	expect(await screen.findByText('Weekly hygiene')).toBeTruthy();
	expect(screen.getByRole('button', { name: 'Run now: Weekly hygiene' })).toBeTruthy();
	expect(screen.queryByText('Dispatch Other')).toBeNull();
	expect(screen.queryByText('Observe Other')).toBeNull();
	expect(screen.queryByText('Other probe')).toBeNull();
	const tests = screen.getByRole('region', { name: 'Connection tests' });
	expect(within(tests).getByRole('link', { name: 'Connections' }).getAttribute('href')).toBe(
		'/projects/p1?tab=connections'
	);
	// Dispatch follows the project's interval, so it has no controls of its own here.
	expect(screen.queryByRole('button', { name: 'Edit Dispatch Application' })).toBeNull();
	expect(screen.queryByRole('dialog')).toBeNull();
});

test('automation pauses, edits and deletes a CI observation schedule in place', async () => {
	mockOwnedSchedules();
	vi.stubGlobal('confirm', vi.fn().mockReturnValue(true));
	api.PATCH.mockResolvedValue({ data: {} });
	api.PUT.mockResolvedValue({ data: {} });
	api.DELETE.mockResolvedValue({ data: {} });
	const user = userEvent.setup();
	render(ProjectDetailView, { projectId: 'p1', tab: 'automation' });
	await screen.findByText('Observe Application');

	await user.click(screen.getByRole('button', { name: 'Pause' }));
	await waitFor(() =>
		expect(api.PATCH).toHaveBeenCalledWith('/api/v1/schedule_configs/{schedule_config_id}', {
			params: { path: { schedule_config_id: 'o1' } },
			body: { enabled: false }
		})
	);

	await user.click(await screen.findByRole('button', { name: 'Edit Observe Application' }));
	const dialog = await screen.findByRole('dialog');
	const pulls = within(dialog).getByLabelText('Pull request numbers') as HTMLInputElement;
	expect(pulls.value).toBe('42, 105');
	await fireEvent.input(pulls, { target: { value: '42, 7' } });
	await user.click(within(dialog).getByRole('button', { name: 'Save changes' }));
	await waitFor(() =>
		expect(api.PUT).toHaveBeenCalledWith('/api/v1/schedule_configs/{schedule_config_id}', {
			params: { path: { schedule_config_id: 'o1' } },
			body: expect.objectContaining({
				task_func: 'pipeline.observe_project',
				payload: { project_id: 'p1', pull_numbers: [42, 7] }
			})
		})
	);
	await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
	await waitFor(() => expect(getComputedStyle(document.body).pointerEvents).not.toBe('none'));

	await user.click(screen.getByRole('button', { name: 'Delete Observe Application' }));
	await waitFor(() =>
		expect(api.DELETE).toHaveBeenCalledWith('/api/v1/schedule_configs/{schedule_config_id}', {
			params: { path: { schedule_config_id: 'o1' } }
		})
	);
});

test('a new CI observation is created for this project only', async () => {
	mockOwnedSchedules();
	api.POST.mockResolvedValue({ data: {} });
	const user = userEvent.setup();
	render(ProjectDetailView, { projectId: 'p1', tab: 'automation' });
	await screen.findByText('Observe Application');

	await user.click(screen.getByRole('button', { name: 'New CI observation' }));
	const dialog = await screen.findByRole('dialog');
	// The project dispatch schedule is derived from the project; it cannot be created here.
	expect(within(dialog).queryByText(/Dispatch/)).toBeNull();
	await fireEvent.input(within(dialog).getByLabelText('Pull request numbers'), {
		target: { value: '9' }
	});
	await user.click(within(dialog).getByRole('button', { name: 'Create schedule' }));
	await waitFor(() =>
		expect(api.POST).toHaveBeenCalledWith('/api/v1/schedule_configs', {
			body: {
				name: 'Observe Application',
				description: 'CI observation for Application',
				task_func: 'pipeline.observe_project',
				cron_expression: null,
				interval_seconds: 300,
				payload: { project_id: 'p1', pull_numbers: [9] },
				enabled: true
			}
		})
	);
});

test('the automation policy saves the revision it started from and keeps untouched fields', async () => {
	const user = userEvent.setup();
	render(ProjectDetailView, { projectId: 'p1', tab: 'automation' });
	const limit = (await screen.findByLabelText('Max runs in flight')) as HTMLInputElement;
	expect(limit.value).toBe('2');
	await fireEvent.input(limit, { target: { value: '' } });
	await user.click(screen.getByRole('button', { name: 'Save Changes' }));

	await waitFor(() => expect(api.PATCH).toHaveBeenCalledTimes(1));
	const [, request] = api.PATCH.mock.calls[0];
	expect(request.body).toMatchObject({ name: 'Application', expected_revision: 4 });
	expect(request.body.github.verification).toEqual(project.github.verification);
	expect(request.body.github.automation).toEqual({
		...project.github.automation,
		max_in_flight_runs: null
	});
});

test('project deletion lives in Settings, asks first and explains a refusal', async () => {
	vi.stubGlobal('confirm', vi.fn().mockReturnValueOnce(false).mockReturnValue(true));
	api.DELETE.mockResolvedValue({ error: { detail: 'Project still has pipeline runs' } });
	const user = userEvent.setup();
	render(ProjectDetailView, { projectId: 'p1', tab: 'settings' });
	await user.click(await screen.findByRole('button', { name: 'Delete project' }));
	expect(api.DELETE).not.toHaveBeenCalled();
	await user.click(screen.getByRole('button', { name: 'Delete project' }));
	await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Project still has pipeline runs'));
});
