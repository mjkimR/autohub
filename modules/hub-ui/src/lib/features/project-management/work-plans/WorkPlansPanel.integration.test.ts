import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import type { components } from '$lib/api';
import WorkPlansPanel from './WorkPlansPanel.svelte';
import WorkPlanForm from './WorkPlanForm.svelte';

const { api } = vi.hoisted(() => ({ api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
const item = {
	id: 'i1',
	key: 'a',
	title: 'Schema',
	description: 'Create schema',
	acceptance: 'Tests pass',
	state: 'waiting',
	detail: null,
	depends_on: [],
	pipeline_run_id: null,
	pipeline_run_retired_at: null,
	pull_url: null,
	merge_sha: null,
	started_at: null,
	completed_at: null,
	issue: { issue_url: null, error: 'Rate limited', pending: true }
} satisfies components['schemas']['WorkItemRead'];
const plan = {
	id: 'plan1',
	project_id: 'p1',
	title: 'Login',
	description: 'Login feature',
	base_branch: 'main',
	state: 'active',
	revision: 3,
	created_at: '2026-09-22T00:00:00Z',
	completed_at: null,
	depends_on: [],
	items: [item],
	issue: {
		issue_url: 'https://github.com/owner/app/issues/1',
		error: 'Rate limited',
		pending: true
	}
} satisfies components['schemas']['WorkPlanRead'];
const project = {
	id: 'p1',
	name: 'Application',
	enabled: true,
	github: { repository: 'owner/app' }
} as components['schemas']['ProjectRead'];

beforeEach(() => {
	api.GET.mockReset().mockResolvedValue({
		data: { items: [structuredClone(plan)], total_count: 1 }
	});
	api.POST.mockReset().mockResolvedValue({ data: plan });
	api.PUT.mockReset().mockResolvedValue({ data: plan });
});
afterEach(() => {
	cleanup();
	vi.restoreAllMocks();
});

test('shows sync failure separately and pauses with the observed revision', async () => {
	render(WorkPlansPanel, { project });
	await screen.findByText('Login');
	expect(screen.getByText(/Work continues independently/)).toBeTruthy();
	await fireEvent.click(screen.getByRole('button', { name: 'Pause' }));
	await waitFor(() =>
		expect(api.POST).toHaveBeenCalledWith(
			'/api/v1/projects/{project_id}/work-plans/{plan_id}/control',
			{
				params: { path: { project_id: 'p1', plan_id: 'plan1' } },
				body: { action: 'pause', expected_revision: 3 }
			}
		)
	);
});

test('revoked plans retain started tasks and expose no resume', async () => {
	api.GET.mockResolvedValue({
		data: {
			items: [
				{
					...plan,
					state: 'revoked',
					items: [{ ...item, state: 'running', started_at: '2026-09-22T00:00:00Z' }]
				}
			],
			total_count: 1
		}
	});
	render(WorkPlansPanel, { project });
	await screen.findByText('Login');
	expect(screen.getByText('running')).toBeTruthy();
	expect(screen.queryByRole('button', { name: 'Resume' })).toBeNull();
	expect(screen.queryByRole('button', { name: 'Edit' })).toBeNull();
});

test('bulk task input creates one plan and preserves item dependencies', async () => {
	const onsaved = vi.fn();
	render(WorkPlanForm, { projectId: 'p1', plans: [], onsaved, oncancel: vi.fn() });
	await fireEvent.input(screen.getByLabelText('Plan title'), { target: { value: 'Feature' } });
	await fireEvent.click(screen.getByRole('button', { name: 'Import task list' }));
	const tasks = [
		{ key: 'a', title: 'Schema', description: 'Create schema', acceptance: 'Tests pass' },
		{
			key: 'b',
			title: 'API',
			description: 'Create API',
			acceptance: 'Tests pass',
			depends_on: ['a']
		}
	];
	await fireEvent.input(screen.getByLabelText('Task list'), {
		target: { value: JSON.stringify(tasks) }
	});
	await fireEvent.click(screen.getByRole('button', { name: 'Use task list' }));
	await fireEvent.click(screen.getByRole('button', { name: 'Add and start' }));
	await waitFor(() => expect(onsaved).toHaveBeenCalledOnce());
	expect(api.POST.mock.calls[0][1].body.items[1].depends_on).toEqual(['a']);
	expect(api.POST.mock.calls[0][1].body.base_branch).toBe('main');
});

test('failed save retains specification and surfaces the API error', async () => {
	api.PUT.mockResolvedValue({ error: { detail: 'Work plan changed; reload before modifying it' } });
	const onsaved = vi.fn();
	render(WorkPlanForm, {
		projectId: 'p1',
		plans: [plan],
		editing: plan,
		onsaved,
		oncancel: vi.fn()
	});
	await fireEvent.click(screen.getByRole('button', { name: 'Save plan' }));
	await screen.findByRole('alert');
	expect((screen.getByLabelText('Plan title') as HTMLInputElement).value).toBe('Login');
	expect(onsaved).not.toHaveBeenCalled();
});
