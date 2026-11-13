import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import RunPageView from './RunPageView.svelte';
import RunRedirect from './RunRedirect.svelte';

const { api, goto } = vi.hoisted(() => ({
	api: { GET: vi.fn(), POST: vi.fn() },
	goto: vi.fn()
}));
vi.mock('$lib/api', () => ({ api }));
vi.mock('$app/navigation', () => ({ goto }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

const run = {
	id: 'run-1',
	project_id: 'project-1',
	pull_number: 7,
	pull_url: 'https://github.com/owner/app/pull/7',
	pull_snapshot: { title: 'Ship the feature' },
	branch: 'feature/7',
	state: 'paused',
	pause_reason: 'Waiting for the operator',
	revision: 2,
	lease_owner: null,
	lease_expires_at: null,
	next_action_at: null,
	created_at: '2026-09-14T00:00:00Z',
	updated_at: '2026-09-14T01:00:00Z'
};
const attempt = {
	id: 'attempt-1',
	attempt_number: 1,
	kind: 'implementation',
	state: 'failed',
	idempotency_key: 'key-1',
	request_digest: 'digest-1',
	failure_code: 'CI_FAILED',
	failure_detail: 'Tests failed',
	created_at: '2026-09-14T00:00:00Z'
};
let current: Record<string, unknown>;
let decisions: unknown[];
let plans: unknown[];
let attempts: { data?: unknown; error?: unknown };
let questions: unknown[];

beforeEach(() => {
	current = { ...run };
	decisions = [];
	plans = [];
	attempts = { data: { items: [attempt], summary: null } };
	questions = [];
	goto.mockReset();
	api.POST.mockReset();
	api.GET.mockReset();
	api.GET.mockImplementation(async (path: string) => {
		if (path === '/api/v1/pipeline-runs/{run_id}') return { data: current };
		if (path === '/api/v1/projects/{project_id}') return { data: { name: 'Scheduler' } };
		if (path === '/api/v1/pipeline-runs/decisions')
			return { data: { items: decisions, has_more: false, next_cursor: null } };
		if (path === '/api/v1/pipeline-runs/{run_id}/questions')
			return {
				data: { items: questions, total_count: questions.length, run_revision: current.revision }
			};
		if (path === '/api/v1/pipeline-runs/{run_id}/attempts') return attempts;
		if (path === '/api/v1/projects/{project_id}/work-plans')
			return { data: { items: plans, total_count: plans.length } };
		return { data: { items: [] } };
	});
});
afterEach(() => {
	cleanup();
	vi.restoreAllMocks();
});

const renderPage = () => render(RunPageView, { projectId: 'project-1', runId: 'run-1' });

test('shows identity, breadcrumb, wait reason, decisions and attempts on one page', async () => {
	renderPage();
	expect(await screen.findByRole('heading', { level: 1, name: 'Ship the feature' })).toBeTruthy();
	const crumbs = screen.getByRole('navigation', { name: 'Breadcrumb' });
	expect(crumbs.textContent).toContain('Scheduler');
	expect(screen.getByRole('link', { name: 'Runs' }).getAttribute('href')).toBe(
		'/projects/project-1?tab=runs'
	);
	expect(screen.getByText('Waiting for the operator')).toBeTruthy();
	expect(screen.getByRole('heading', { name: 'Decisions' })).toBeTruthy();
	expect(await screen.findByText('CI_FAILED')).toBeTruthy();
	expect(screen.getByRole('button', { name: 'Resume' })).toBeTruthy();
	expect(screen.getByRole('button', { name: 'Advance now' })).toBeTruthy();
});

test('a pending question replaces Resume with Answer question', async () => {
	decisions = [{ run_id: 'run-1', kind: 'run-question', question_state: 'open', actionable: true }];
	renderPage();
	expect((await screen.findByRole('link', { name: 'Answer question' })).getAttribute('href')).toBe(
		'#decisions'
	);
	expect(screen.getByText('Question waiting')).toBeTruthy();
	expect(screen.queryByRole('button', { name: 'Resume' })).toBeNull();
});

test('resume acts on the current revision and reloads the run', async () => {
	vi.spyOn(window, 'confirm').mockReturnValue(true);
	api.POST.mockResolvedValue({ data: { ...run, state: 'queued' } });
	const user = userEvent.setup();
	renderPage();
	await user.click(await screen.findByRole('button', { name: 'Resume' }));
	await waitFor(() =>
		expect(api.POST).toHaveBeenCalledWith('/api/v1/pipeline-runs/{run_id}/resume', {
			params: { path: { run_id: 'run-1' } },
			body: { request_id: expect.any(String), expected_revision: 2 }
		})
	);
	await waitFor(() =>
		expect(
			api.GET.mock.calls.filter(([path]) => path === '/api/v1/pipeline-runs/{run_id}').length
		).toBeGreaterThan(2)
	);
});

test('a failed Work Item run links to that Work Item recovery', async () => {
	current = {
		...run,
		state: 'failed',
		pause_reason: null,
		related_origins: [{ kind: 'work_plan', id: 'item-1', work_plan_id: 'plan-1' }]
	};
	plans = [
		{
			id: 'plan-1',
			title: 'Q4 plan',
			items: [{ id: 'item-1', key: 'T1', title: 'Add API', pipeline_run_id: 'run-1' }]
		}
	];
	renderPage();
	expect(
		(await screen.findByRole('link', { name: 'Open Work Item recovery' })).getAttribute('href')
	).toBe('/projects/project-1?tab=plans#work-item-item-1');
	expect(screen.getByRole('link', { name: 'Work Item item-1' })).toBeTruthy();
	expect(
		api.GET.mock.calls.some(([path]) => path === '/api/v1/projects/{project_id}/work-plans')
	).toBe(false);
	expect(screen.getByRole('heading', { name: 'Next step' })).toBeTruthy();
	expect(screen.queryByRole('link', { name: 'Next step' })).toBeNull();
});

test('a failed run without a Work Item points to replacement work', async () => {
	current = { ...run, state: 'failed', pause_reason: null };
	renderPage();
	expect(await screen.findByText(/No Work Item links to this run/)).toBeTruthy();
	expect(screen.getByRole('link', { name: 'Enroll PR' }).getAttribute('href')).toBe(
		'/projects/project-1?tab=runs'
	);
	expect(screen.getByRole('link', { name: /Work Plans/ }).getAttribute('href')).toBe(
		'/projects/project-1?tab=plans'
	);
});

test('an SDD run links back to its unit in the repository view', async () => {
	current = { ...run, sdd_snapshot: { spec_dir: 'specs/2026-10/feature' } };
	renderPage();
	expect(
		(await screen.findByRole('link', { name: 'specs/2026-10/feature' })).getAttribute('href')
	).toBe('/projects/project-1?tab=repository&unit=specs%2F2026-10%2Ffeature&ref=feature%2F7');
});

test('a missing run shows not found with a way back', async () => {
	api.GET.mockImplementation(async (path: string) =>
		path === '/api/v1/pipeline-runs/{run_id}'
			? { error: { detail: 'Not found' }, response: { status: 404 } }
			: { data: { items: [], name: 'Scheduler' } }
	);
	renderPage();
	expect(await screen.findByRole('heading', { name: 'PR run not found' })).toBeTruthy();
	expect(screen.getByRole('link', { name: /Back to project runs/ }).getAttribute('href')).toBe(
		'/projects/project-1?tab=runs'
	);
});

test('a failed refresh keeps the last loaded run beside a retry banner', async () => {
	const user = userEvent.setup();
	renderPage();
	await screen.findByRole('heading', { level: 1, name: 'Ship the feature' });
	const previous = api.GET.getMockImplementation()!;
	api.GET.mockImplementation(async (path: string, options?: unknown) =>
		path === '/api/v1/pipeline-runs/{run_id}'
			? { error: { detail: 'Hub unavailable' }, response: { status: 503 } }
			: previous(path, options)
	);
	await user.click(screen.getByRole('button', { name: 'Refresh' }));
	expect((await screen.findByRole('alert')).textContent).toContain('Hub unavailable');
	expect(screen.getByRole('heading', { level: 1, name: 'Ship the feature' })).toBeTruthy();
});

test('attempt failures show a retry instead of an empty history', async () => {
	attempts = { error: { detail: 'History temporarily unavailable' } };
	const user = userEvent.setup();
	renderPage();
	await screen.findByText('History temporarily unavailable');
	expect(screen.queryByText('No execution attempts recorded yet')).toBeNull();
	attempts = { data: { items: [], summary: null } };
	const retry = screen
		.getAllByRole('button', { name: 'Retry' })
		.find((button) => button.closest('#attempts'))!;
	await user.click(retry);
	await screen.findByText('No execution attempts recorded yet');
});

test('a run opened under the wrong project redirects to its own project', async () => {
	current = { ...run, project_id: 'project-2' };
	renderPage();
	await waitFor(() =>
		expect(goto).toHaveBeenCalledWith('/projects/project-2/runs/run-1', { replaceState: true })
	);
});

test('/runs/<id> resolves the project and replaces itself with the run page', async () => {
	window.history.replaceState({}, '', '/runs/run-1#attempts');
	render(RunRedirect, { runId: 'run-1' });
	await waitFor(() =>
		expect(goto).toHaveBeenCalledWith('/projects/project-1/runs/run-1#attempts', {
			replaceState: true
		})
	);
	window.history.replaceState({}, '', '/');
});

test.each([
	['decisions', 'paused'],
	['attempts', 'paused'],
	['next-step', 'failed']
])('the #%s section link focuses that section once content renders', async (section, state) => {
	current = { ...run, state, pause_reason: state === 'failed' ? null : run.pause_reason };
	window.history.replaceState({}, '', `/projects/project-1/runs/run-1#${section}`);
	try {
		renderPage();
		await waitFor(() => expect(document.activeElement?.id).toBe(section));
	} finally {
		window.history.replaceState({}, '', '/');
	}
});

test('an incomplete decisions page keeps the run page conservative', async () => {
	api.GET.mockImplementation(async (path: string) => {
		if (path === '/api/v1/pipeline-runs/{run_id}') return { data: current };
		if (path === '/api/v1/projects/{project_id}') return { data: { name: 'Scheduler' } };
		if (path === '/api/v1/pipeline-runs/decisions')
			return {
				data: {
					items: [{ run_id: 'other', kind: 'native-workflow', actionable: true }],
					has_more: true,
					next_cursor: 'next'
				}
			};
		if (path === '/api/v1/pipeline-runs/{run_id}/attempts') return attempts;
		return { data: { items: [], total_count: 0, run_revision: current.revision } };
	});
	renderPage();
	await screen.findByRole('heading', { level: 1, name: 'Ship the feature' });
	expect(
		api.GET.mock.calls.filter(([path]) => path === '/api/v1/pipeline-runs/decisions')
	).toHaveLength(5);
	// Unknown decisions: no decision marker or decision action, Resume only as a secondary action.
	expect(screen.queryByText('Question waiting')).toBeNull();
	expect(screen.queryByRole('link', { name: 'Answer question' })).toBeNull();
	expect(screen.getByRole('button', { name: 'Resume' })).toBeTruthy();
});

test('header Refresh keeps the Decisions draft instead of remounting it', async () => {
	questions = [
		{
			id: 'question-1',
			question: 'Keep existing behavior?',
			state: 'open',
			actor: 'agent',
			created_at: '2026-09-30T00:00:00Z',
			answers: []
		}
	];
	const user = userEvent.setup();
	renderPage();
	const answer = (await screen.findByLabelText('Your answer')) as HTMLTextAreaElement;
	await waitFor(() => expect(answer.disabled).toBe(false));
	await user.type(answer, 'Draft reply');
	await user.click(screen.getByRole('button', { name: 'Refresh' }));
	await waitFor(() =>
		expect(
			api.GET.mock.calls.filter(([path]) => path === '/api/v1/pipeline-runs/{run_id}/attempts')
		).toHaveLength(2)
	);
	expect(screen.getByLabelText('Your answer')).toBe(answer);
	expect(answer.value).toBe('Draft reply');
});
