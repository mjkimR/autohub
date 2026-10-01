import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import type { components } from '$lib/api';
import WorkPlansPanel from './WorkPlansPanel.svelte';
import WorkPlanForm from './WorkPlanForm.svelte';

const { api } = vi.hoisted(() => ({
	api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), PATCH: vi.fn() }
}));
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
	registration_request_id: null,
	id: 'plan1',
	project_id: 'p1',
	group_key: null,
	title: 'Login',
	description: 'Login feature',
	base_branch: 'main',
	state: 'active',
	revision: 3,
	created_at: '2026-09-22T00:00:00Z',
	scheduled_at: null,
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
	api.PATCH.mockReset().mockResolvedValue({ data: plan });
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
				body: { action: 'pause', expected_revision: 3, reason: '' }
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

test('waiting tasks explain themselves from dependencies when the API sends no detail', async () => {
	api.GET.mockResolvedValue({
		data: {
			items: [
				{
					...plan,
					items: [
						{ ...item, state: 'running' },
						{ ...item, id: 'i2', key: 'b', title: 'API', depends_on: ['a'] }
					]
				}
			],
			total_count: 1
		}
	});
	render(WorkPlansPanel, { project });
	await screen.findByText('Login');
	expect(screen.getByText('Waiting for tasks: a')).toBeTruthy();
});

test('bulk task input creates one plan and preserves item dependencies', async () => {
	const onsaved = vi.fn();
	render(WorkPlanForm, { projectId: 'p1', plans: [], onsaved, oncancel: vi.fn() });
	await fireEvent.input(screen.getByLabelText('Plan title'), { target: { value: 'Feature' } });
	await fireEvent.change(screen.getByLabelText('Save as'), { target: { value: 'active' } });
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

test('creates a reservation using local input converted to UTC', async () => {
	render(WorkPlanForm, {
		projectId: 'p1',
		plans: [],
		onsaved: vi.fn(),
		oncancel: vi.fn()
	});
	await fireEvent.input(screen.getByLabelText('Plan title'), {
		target: { value: 'Scheduled work' }
	});
	await fireEvent.change(screen.getByLabelText('Save as'), { target: { value: 'active' } });
	await fireEvent.click(screen.getByRole('button', { name: 'Add task' }));
	await fireEvent.input(screen.getByLabelText('Title'), { target: { value: 'Task' } });
	await fireEvent.input(screen.getByLabelText('Specification'), {
		target: { value: 'Implement it' }
	});
	await fireEvent.input(screen.getByLabelText('Acceptance criteria'), {
		target: { value: 'Tests pass' }
	});
	const local = '2099-10-01T09:30';
	await fireEvent.input(screen.getByLabelText('Start no earlier than'), {
		target: { value: local }
	});
	await fireEvent.click(screen.getByRole('button', { name: 'Add and schedule' }));
	await waitFor(() => expect(api.POST).toHaveBeenCalledOnce());
	expect(api.POST.mock.calls[0][1].body.scheduled_at).toBe(new Date(local).toISOString());
});

test('editing preserves an existing instant and allows clearing the reservation', async () => {
	const scheduled = { ...plan, scheduled_at: '2099-10-01T09:30:12.123456+09:00' };
	render(WorkPlanForm, {
		projectId: 'p1',
		plans: [scheduled],
		editing: scheduled,
		onsaved: vi.fn(),
		oncancel: vi.fn()
	});
	const input = screen.getByLabelText('Start no earlier than') as HTMLInputElement;
	expect(new Date(input.value).getTime()).toBe(new Date(scheduled.scheduled_at).getTime());
	await fireEvent.click(screen.getByRole('button', { name: 'Save plan' }));
	await waitFor(() => expect(api.PUT).toHaveBeenCalledOnce());
	expect(api.PUT.mock.calls[0][1].body.scheduled_at).toBe(scheduled.scheduled_at);
	await fireEvent.input(input, { target: { value: '' } });
	await fireEvent.click(screen.getByRole('button', { name: 'Save plan' }));
	await waitFor(() => expect(api.PUT).toHaveBeenCalledTimes(2));
	expect(api.PUT.mock.calls[1][1].body.scheduled_at).toBeNull();
});

test('future reservations show a waiting reason while paused plans retain the pause reason', async () => {
	api.GET.mockResolvedValue({
		data: {
			items: [{ ...plan, scheduled_at: '2099-10-01T00:00:00Z' }],
			total_count: 1
		}
	});
	render(WorkPlansPanel, { project });
	expect(await screen.findByText(/Scheduled; waiting until/)).toBeTruthy();
	expect(screen.getByText(/Start no earlier than:/)).toBeTruthy();
	api.GET.mockResolvedValue({
		data: {
			items: [{ ...plan, state: 'paused', scheduled_at: '2099-10-01T00:00:00Z' }],
			total_count: 1
		}
	});
	await fireEvent.click(screen.getByRole('button', { name: 'Refresh' }));
	expect(await screen.findByText('Plan paused')).toBeTruthy();
	expect(screen.queryByText(/Scheduled; waiting until/)).toBeNull();
});

test('saves a title-only seed without requesting execution', async () => {
	render(WorkPlanForm, { projectId: 'p1', plans: [], onsaved: vi.fn(), oncancel: vi.fn() });
	await fireEvent.input(screen.getByLabelText('Plan title'), { target: { value: 'New idea' } });
	await fireEvent.click(screen.getByRole('button', { name: 'Save draft' }));
	await waitFor(() => expect(api.POST).toHaveBeenCalledOnce());
	expect(api.POST.mock.calls[0][1].body).toMatchObject({
		title: 'New idea',
		state: 'draft',
		scheduled_at: null,
		items: []
	});
});

test('proposal edits permit removing all items and explain returning to draft', async () => {
	render(WorkPlanForm, {
		projectId: 'p1',
		plans: [],
		editing: { ...plan, state: 'proposed' },
		onsaved: vi.fn(),
		oncancel: vi.fn()
	});
	expect(screen.getByText(/Saving changes returns this proposal to Draft/)).toBeTruthy();
	await fireEvent.click(screen.getByRole('button', { name: 'Remove task' }));
	await fireEvent.click(screen.getByRole('button', { name: 'Save plan' }));
	await waitFor(() => expect(api.PUT).toHaveBeenCalledOnce());
	expect(api.PUT.mock.calls[0][1].body.items).toEqual([]);
	expect(api.PUT.mock.calls[0][1].body.expected_revision).toBe(3);
});

test('decision view isolates proposals and submits the observed revision', async () => {
	api.GET.mockResolvedValue({
		data: {
			items: [plan, { ...plan, id: 'proposal', title: 'Candidate', state: 'proposed' }],
			total_count: 2
		}
	});
	render(WorkPlansPanel, { project });
	await screen.findByText('Candidate');
	await fireEvent.change(screen.getByLabelText('Show'), { target: { value: 'proposed' } });
	expect(screen.queryByText('Login')).toBeNull();
	expect(screen.getByText(/Proposed · decision needed/)).toBeTruthy();
	await fireEvent.click(screen.getByRole('button', { name: 'Mark ready' }));
	await waitFor(() =>
		expect(api.POST).toHaveBeenCalledWith(
			'/api/v1/projects/{project_id}/work-plans/{plan_id}/control',
			{
				params: { path: { project_id: 'p1', plan_id: 'proposal' } },
				body: { action: 'ready', expected_revision: 3, reason: '' }
			}
		)
	);
});

test.each(['draft', 'proposed'])(
	'renames %s task keys and preserves dependent references',
	async (state) => {
		const editing = {
			...plan,
			state,
			items: [item, { ...item, id: 'i2', key: 'b', title: 'Consumer', depends_on: ['a'] }]
		};
		render(WorkPlanForm, {
			projectId: 'p1',
			plans: [],
			editing,
			onsaved: vi.fn(),
			oncancel: vi.fn()
		});
		const key = screen.getAllByLabelText('Key')[0] as HTMLInputElement;
		// An empty or colliding intermediate value must not rewrite the graph.
		await fireEvent.input(key, { target: { value: '' } });
		expect(key.checkValidity()).toBe(false);
		await fireEvent.input(key, { target: { value: 'b' } });
		expect(key.checkValidity()).toBe(false);
		await fireEvent.input(key, { target: { value: 'base' } });
		expect(key.checkValidity()).toBe(true);
		await fireEvent.input(key, { target: { value: 'foundation' } });
		await fireEvent.click(screen.getByRole('button', { name: 'Save plan' }));
		await waitFor(() => expect(api.PUT).toHaveBeenCalledOnce());
		expect(api.PUT.mock.calls[0][1].body.items).toMatchObject([
			{ key: 'foundation', depends_on: [] },
			{ key: 'b', depends_on: ['foundation'] }
		]);
		expect((screen.getByLabelText('foundation: Schema') as HTMLInputElement).checked).toBe(true);
		// Removing an invalid key field must not leave its validity error on the next task.
		await fireEvent.input(key, { target: { value: 'b' } });
		await fireEvent.click(screen.getAllByRole('button', { name: 'Remove task' })[0]);
		expect((screen.getByLabelText('Key') as HTMLInputElement).checkValidity()).toBe(true);
	}
);

function renderKeyEditor(state: 'draft' | 'proposed' = 'draft') {
	render(WorkPlanForm, {
		projectId: 'p1',
		plans: [],
		editing: {
			...plan,
			state,
			items: [
				item,
				{ ...item, id: 'i2', key: 'b', title: 'Consumer', depends_on: ['a'] },
				{ ...item, id: 'i3', key: 'c', title: 'Final', depends_on: ['a', 'b'] }
			]
		},
		onsaved: vi.fn(),
		oncancel: vi.fn()
	});
	return screen.getAllByLabelText('Key') as HTMLInputElement[];
}

test('group filters distinguish all, null, and literal keys alongside state filters', async () => {
	api.GET.mockResolvedValue({
		data: {
			items: [
				plan,
				{ ...plan, id: 'a', title: 'Game A', group_key: 'game-a' },
				{ ...plan, id: 'b', title: 'Proposal A', group_key: 'game-a', state: 'proposed' },
				{ ...plan, id: 'c', title: 'Literal null', group_key: '(null)' }
			],
			total_count: 4
		}
	});
	render(WorkPlansPanel, { project });
	await screen.findByText('Game A');
	await fireEvent.change(screen.getByLabelText('Group'), { target: { value: 'null' } });
	expect(screen.getByText('Login')).toBeTruthy();
	expect(screen.queryByText('Game A')).toBeNull();
	expect(screen.queryByText('Literal null')).toBeNull();
	await fireEvent.change(screen.getByLabelText('Group'), {
		target: { value: JSON.stringify('game-a') }
	});
	await fireEvent.change(screen.getByLabelText('Show'), { target: { value: 'proposed' } });
	expect(screen.getByText('Proposal A')).toBeTruthy();
	expect(screen.queryByText('Game A')).toBeNull();
});

test('saves a normalized group on creation', async () => {
	render(WorkPlanForm, { projectId: 'p1', plans: [], onsaved: vi.fn(), oncancel: vi.fn() });
	await fireEvent.input(screen.getByLabelText('Plan title'), { target: { value: 'New idea' } });
	await fireEvent.input(screen.getByLabelText('Group key'), { target: { value: ' game-a ' } });
	await fireEvent.click(screen.getByRole('button', { name: 'Save draft' }));
	await waitFor(() => expect(api.POST).toHaveBeenCalledOnce());
	expect(api.POST.mock.calls[0][1].body.group_key).toBe('game-a');
});

test('group editing survives group and state filters with its input and cancel action', async () => {
	api.GET.mockResolvedValue({
		data: {
			items: [
				{ ...plan, group_key: 'game-a' },
				{ ...plan, id: 'other', title: 'Other game', group_key: 'game-b', state: 'proposed' }
			],
			total_count: 2
		}
	});
	render(WorkPlansPanel, { project });
	await screen.findByText('Login');
	await fireEvent.change(screen.getByLabelText('Group'), {
		target: { value: JSON.stringify('game-a') }
	});
	await fireEvent.click(screen.getByRole('button', { name: 'Change group' }));
	await fireEvent.input(screen.getByLabelText('Group key'), { target: { value: 'shared-work' } });
	await fireEvent.change(screen.getByLabelText('Group'), {
		target: { value: JSON.stringify('game-b') }
	});
	await fireEvent.change(screen.getByLabelText('Show'), { target: { value: 'proposed' } });
	expect(screen.queryByText('Login', { selector: 'h3' })).toBeNull();
	expect(screen.getByRole('heading', { name: 'Change group: Login' })).toBeTruthy();
	expect((screen.getByLabelText('Group key') as HTMLInputElement).value).toBe('shared-work');
	await fireEvent.change(screen.getByLabelText('Group'), { target: { value: 'all' } });
	await fireEvent.change(screen.getByLabelText('Show'), { target: { value: 'all' } });
	expect((screen.getByLabelText('Group key') as HTMLInputElement).value).toBe('shared-work');
	await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
	expect((screen.getByRole('button', { name: 'Add plan' }) as HTMLButtonElement).disabled).toBe(
		false
	);
	for (const button of screen.getAllByRole('button', { name: 'Change group' })) {
		expect((button as HTMLButtonElement).disabled).toBe(false);
	}
	expect(api.PATCH).not.toHaveBeenCalled();
});

test('refresh after a group conflict preserves input and retries with the newly displayed revision', async () => {
	render(WorkPlansPanel, { project });
	await screen.findByText('Login');
	await fireEvent.click(screen.getByRole('button', { name: 'Change group' }));
	await fireEvent.input(screen.getByLabelText('Group key'), { target: { value: 'game-a' } });
	api.PATCH.mockResolvedValueOnce({
		error: { detail: 'Work plan changed; reload before modifying it' }
	});
	await fireEvent.click(screen.getByRole('button', { name: 'Save group' }));
	await screen.findByRole('alert');
	api.GET.mockResolvedValue({
		data: { items: [{ ...plan, group_key: 'platform', revision: 4 }], total_count: 1 }
	});
	await fireEvent.click(screen.getByRole('button', { name: 'Refresh' }));
	await screen.findByText('Current saved group: "platform"');
	expect(screen.getByRole('status').textContent).toContain('Your input is preserved');
	expect((screen.getByLabelText('Group key') as HTMLInputElement).value).toBe('game-a');
	expect(api.PATCH).toHaveBeenCalledTimes(1);
	await fireEvent.click(screen.getByRole('button', { name: 'Save group' }));
	await waitFor(() => expect(api.PATCH).toHaveBeenCalledTimes(2));
	expect(api.PATCH.mock.calls[0][1].body.expected_revision).toBe(3);
	expect(api.PATCH.mock.calls[1][1].body).toEqual({
		group_key: 'game-a',
		expected_revision: 4,
		reason: ''
	});
	await waitFor(() => expect(screen.queryByLabelText('Group key')).toBeNull());
	expect(api.POST).not.toHaveBeenCalled();
	expect(api.PUT).not.toHaveBeenCalled();
});

test('failed refresh keeps the group draft and last observed revision', async () => {
	render(WorkPlansPanel, { project });
	await screen.findByText('Login');
	await fireEvent.click(screen.getByRole('button', { name: 'Change group' }));
	await fireEvent.input(screen.getByLabelText('Group key'), { target: { value: 'game-a' } });
	api.GET.mockRejectedValueOnce(new Error('Refresh unavailable'));
	await fireEvent.click(screen.getByRole('button', { name: 'Refresh' }));
	await screen.findByText('Refresh unavailable');
	expect((screen.getByLabelText('Group key') as HTMLInputElement).value).toBe('game-a');
	expect(api.PATCH).not.toHaveBeenCalled();
	await fireEvent.click(screen.getByRole('button', { name: 'Save group' }));
	await waitFor(() => expect(api.PATCH).toHaveBeenCalledOnce());
	expect(api.PATCH.mock.calls[0][1].body.expected_revision).toBe(3);
});

test('can clear the group of started work without invoking plan control or specification edits', async () => {
	api.GET.mockResolvedValue({
		data: {
			items: [
				{ ...plan, group_key: 'game-a', items: [{ ...item, started_at: '2026-10-01T00:00:00Z' }] }
			],
			total_count: 1
		}
	});
	render(WorkPlansPanel, { project });
	await screen.findByText('Login');
	await fireEvent.click(screen.getByRole('button', { name: 'Change group' }));
	await fireEvent.input(screen.getByLabelText('Group key'), { target: { value: ' ' } });
	api.PATCH.mockResolvedValueOnce({
		error: { detail: 'Work plan changed; reload before modifying it' }
	});
	await fireEvent.click(screen.getByRole('button', { name: 'Save group' }));
	expect(await screen.findByRole('alert')).toBeTruthy();
	expect(screen.getByLabelText('Group key')).toBeTruthy();
	await fireEvent.click(screen.getByRole('button', { name: 'Save group' }));
	await waitFor(() => expect(api.PATCH).toHaveBeenCalledTimes(2));
	expect(api.PATCH.mock.calls[0][1].body).toEqual({
		group_key: null,
		expected_revision: 3,
		reason: ''
	});
	expect(api.POST).not.toHaveBeenCalled();
	expect(api.PUT).not.toHaveBeenCalled();
});

test.each(['draft', 'proposed'] as const)(
	'revalidates %s keys when the conflicting task is renamed',
	async (state) => {
		const [first, second] = renderKeyEditor(state);
		await fireEvent.input(first, { target: { value: 'b' } });
		await fireEvent.click(screen.getByRole('button', { name: 'Save plan' }));
		expect(api.PUT).not.toHaveBeenCalled();
		await fireEvent.input(second, { target: { value: 'renamed' } });
		expect(first.value).toBe('b');
		expect(first.checkValidity()).toBe(true);
		expect(second.checkValidity()).toBe(true);
		await fireEvent.click(screen.getByRole('button', { name: 'Save plan' }));
		await waitFor(() => expect(api.PUT).toHaveBeenCalledOnce());
		expect(api.PUT.mock.calls[0][1].body.items).toEqual([
			{
				key: 'b',
				title: 'Schema',
				description: 'Create schema',
				acceptance: 'Tests pass',
				depends_on: []
			},
			{
				key: 'renamed',
				title: 'Consumer',
				description: 'Create schema',
				acceptance: 'Tests pass',
				depends_on: ['b']
			},
			{
				key: 'c',
				title: 'Final',
				description: 'Create schema',
				acceptance: 'Tests pass',
				depends_on: ['b', 'renamed']
			}
		]);
	}
);

test.each(['draft', 'proposed'] as const)(
	'preserves the entered %s key when deleting the conflicting task',
	async (state) => {
		const [first] = renderKeyEditor(state);
		await fireEvent.input(first, { target: { value: 'b' } });
		await fireEvent.click(screen.getAllByRole('button', { name: 'Remove task' })[1]);
		const remaining = screen.getAllByLabelText('Key') as HTMLInputElement[];
		expect(remaining[0].value).toBe('b');
		expect(remaining[0].checkValidity()).toBe(true);
		await fireEvent.click(screen.getByRole('button', { name: 'Save plan' }));
		await waitFor(() => expect(api.PUT).toHaveBeenCalledOnce());
		expect(api.PUT.mock.calls[0][1].body.items).toMatchObject([
			{ key: 'b', depends_on: [] },
			{ key: 'c', depends_on: ['b'] }
		]);
	}
);

test('swaps task keys without redirecting their dependency relationships', async () => {
	const [first, second] = renderKeyEditor();
	await fireEvent.input(first, { target: { value: 'b' } });
	await fireEvent.input(second, { target: { value: 'a' } });
	await fireEvent.click(screen.getByRole('button', { name: 'Save plan' }));
	await waitFor(() => expect(api.PUT).toHaveBeenCalledOnce());
	expect(api.PUT.mock.calls[0][1].body.items).toMatchObject([
		{ key: 'b', depends_on: [] },
		{ key: 'a', depends_on: ['b'] },
		{ key: 'c', depends_on: ['b', 'a'] }
	]);
});

test('retains an invalid key and blocks saving after other tasks are removed or added', async () => {
	const [first] = renderKeyEditor();
	await fireEvent.input(first, { target: { value: 'invalid!' } });
	await fireEvent.click(screen.getAllByRole('button', { name: 'Remove task' })[1]);
	await fireEvent.click(screen.getByRole('button', { name: 'Add task' }));
	const remaining = screen.getAllByLabelText('Key') as HTMLInputElement[];
	expect(remaining[0].value).toBe('invalid!');
	expect(remaining[0].checkValidity()).toBe(false);
	await fireEvent.click(screen.getByRole('button', { name: 'Save plan' }));
	expect(api.PUT).not.toHaveBeenCalled();
	await fireEvent.input(remaining[0], { target: { value: 'foundation' } });
	await fireEvent.click(screen.getByRole('button', { name: 'Save plan' }));
	await waitFor(() => expect(api.PUT).toHaveBeenCalledOnce());
	expect(api.PUT.mock.calls[0][1].body.items).toMatchObject([
		{ key: 'foundation', depends_on: [] },
		{ key: 'c', depends_on: ['foundation'] },
		{ key: 'task-3', depends_on: [] }
	]);
});
