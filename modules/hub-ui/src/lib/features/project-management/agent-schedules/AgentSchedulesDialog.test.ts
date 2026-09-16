import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import AgentSchedulesDialog from './AgentSchedulesDialog.svelte';

const { api } = vi.hoisted(() => ({
	api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() }
}));

vi.mock('$lib/api', () => ({ api }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

const project = {
	id: 'p1',
	name: 'Application',
	enabled: true,
	revision: 1,
	github: { repository: 'owner/app', github_connector_id: 'g1' }
};
const jules = {
	id: 'j1',
	key: 'personal-jules',
	name: 'Personal Jules',
	kind: 'jules',
	session_work_types: ['task', 'report'],
	pipeline_delivery: false
};
const codex = {
	id: 'c1',
	key: 'personal-codex',
	name: 'Personal Codex',
	kind: 'codex',
	session_work_types: [],
	pipeline_delivery: true
};
const schedule = {
	id: 's1',
	project_id: 'p1',
	schedule_config_id: 'cfg1',
	ai_catalog_id: 'j1',
	work_type: 'report',
	title: 'Weekly hygiene',
	prompt: 'Report stale dependencies.',
	starting_branch: 'main',
	enabled: true,
	cron_expression: '0 9 * * 1',
	interval_seconds: null,
	task_func: 'jules.session',
	next_run_at: '2026-09-21T09:00:00Z',
	last_run_at: null,
	recent_sessions: [
		{
			id: 'ses1',
			state: 'completed',
			created_at: '2026-09-14T09:00:00Z',
			pull_request_url: null,
			result_summary: '3 stale dependencies'
		}
	],
	created_at: '2026-09-10T00:00:00Z',
	updated_at: '2026-09-10T00:00:00Z'
};

beforeEach(() => {
	vi.clearAllMocks();
	api.GET.mockResolvedValue({ data: { items: [schedule] } });
	api.POST.mockResolvedValue({ data: schedule });
});

afterEach(() => {
	cleanup();
	document.body.style.removeProperty('pointer-events');
});

test('lists the project schedules with their recent sessions', async () => {
	render(AgentSchedulesDialog, {
		props: { project, catalogs: [codex, jules], onclose: vi.fn() } as never
	});

	expect(await screen.findByText('Weekly hygiene')).toBeTruthy();
	expect(screen.getByText('report')).toBeTruthy();
	expect(screen.getByText(/cron 0 9 \* \* 1/)).toBeTruthy();
	expect(screen.getByText('3 stale dependencies')).toBeTruthy();
	expect(api.GET).toHaveBeenCalledWith('/api/v1/projects/{project_id}/agent-schedules', {
		params: { path: { project_id: 'p1' } }
	});
});

test('creates a schedule from only session-capable catalogs', async () => {
	const user = userEvent.setup();
	render(AgentSchedulesDialog, {
		props: { project, catalogs: [codex, jules], onclose: vi.fn() } as never
	});
	await screen.findByText('Weekly hygiene');

	await user.click(screen.getByRole('button', { name: 'New schedule' }));

	const catalogSelect = screen.getByLabelText('AI Catalog') as HTMLSelectElement;
	expect(Array.from(catalogSelect.options).map((o) => o.value)).toEqual(['j1']);
	await user.selectOptions(screen.getByLabelText('Work type'), 'report');
	await user.type(screen.getByLabelText('Title'), 'Weekly hygiene');
	await user.type(screen.getByLabelText('Prompt'), 'Report stale dependencies.');
	await user.click(screen.getByRole('button', { name: 'Create schedule' }));

	await waitFor(() =>
		expect(api.POST).toHaveBeenCalledWith('/api/v1/projects/{project_id}/agent-schedules', {
			params: { path: { project_id: 'p1' } },
			body: {
				ai_catalog_id: 'j1',
				work_type: 'report',
				title: 'Weekly hygiene',
				prompt: 'Report stale dependencies.',
				starting_branch: 'main',
				enabled: true,
				cron_expression: '0 9 * * 1',
				interval_seconds: null
			}
		})
	);
});

test('run now queues the schedule', async () => {
	const user = userEvent.setup();
	render(AgentSchedulesDialog, {
		props: { project, catalogs: [jules], onclose: vi.fn() } as never
	});
	await screen.findByText('Weekly hygiene');

	await user.click(screen.getByRole('button', { name: 'Run now' }));

	await waitFor(() =>
		expect(api.POST).toHaveBeenCalledWith(
			'/api/v1/projects/{project_id}/agent-schedules/{schedule_id}/run-now',
			{ params: { path: { project_id: 'p1', schedule_id: 's1' } } }
		)
	);
});
