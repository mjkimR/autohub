import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { toast } from 'svelte-sonner';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import ScheduleConfigsView from './ScheduleConfigsView.svelte';

const { api } = vi.hoisted(() => ({
	api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() }
}));

vi.mock('$lib/api', () => ({ api }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

const config = (id: string, name: string, task_func: string, enabled = true) => ({
	id,
	name,
	description: null,
	task_func,
	cron_expression: null,
	interval_seconds: 600,
	payload: {},
	enabled,
	next_run_at: '2026-09-21T00:10:00Z',
	last_run_at: null,
	created_at: '2026-09-21T00:00:00Z',
	updated_at: '2026-09-21T00:00:00Z'
});

beforeEach(() => {
	api.GET.mockImplementation(async (path: string) =>
		path === '/api/v1/tasks/specs'
			? { data: [{ name: 'hello_world', description: 'Demo', payload_schema: null }] }
			: {
					data: {
						items: [
							config('s1', 'Nightly demo', 'hello_world'),
							config('s2', 'Weekly audit', 'jules.session', false)
						]
					}
				}
	);
	api.POST.mockResolvedValue({ data: { dispatched: 2 } });
	api.PATCH.mockResolvedValue({ data: {} });
});

afterEach(() => {
	cleanup();
	document.body.style.removeProperty('pointer-events');
	vi.clearAllMocks();
});

test('marks schedules a project owns and pauses or resumes one', async () => {
	const user = userEvent.setup();
	render(ScheduleConfigsView);

	expect(await screen.findByText('Nightly demo')).toBeTruthy();
	expect(screen.getAllByText('Project Managed')).toHaveLength(1);

	await user.click(screen.getByRole('button', { name: 'Pause' }));
	await waitFor(() =>
		expect(api.PATCH).toHaveBeenCalledWith('/api/v1/schedule_configs/{schedule_config_id}', {
			params: { path: { schedule_config_id: 's1' } },
			body: { enabled: false }
		})
	);
});

test('shows why the backend refused to change a managed schedule', async () => {
	api.PATCH.mockResolvedValue({
		error: {
			detail: 'This schedule is managed by a project agent schedule; edit or delete it there'
		}
	});
	const user = userEvent.setup();
	render(ScheduleConfigsView);
	await screen.findByText('Weekly audit');

	await user.click(screen.getByRole('button', { name: 'Resume' }));

	await waitFor(() =>
		expect(toast.error).toHaveBeenCalledWith(
			'This schedule is managed by a project agent schedule; edit or delete it there'
		)
	);
});

test('runs a dispatcher tick by hand and creates an interval schedule', async () => {
	const user = userEvent.setup();
	render(ScheduleConfigsView);
	await screen.findByText('Nightly demo');

	await user.click(screen.getByRole('button', { name: /Trigger Dispatcher/ }));
	await waitFor(() =>
		expect(toast.success).toHaveBeenCalledWith('Dispatcher tick completed! Dispatched: 2')
	);

	await user.click(screen.getByRole('button', { name: /New Schedule/ }));
	await fireEvent.input(document.getElementById('scName') as HTMLInputElement, {
		target: { value: ' Hourly demo ' }
	});
	await fireEvent.change(document.getElementById('scTask') as HTMLSelectElement, {
		target: { value: 'hello_world' }
	});
	await user.click(screen.getByRole('button', { name: 'Create Schedule' }));

	await waitFor(() => expect(api.POST).toHaveBeenCalledTimes(2));
	const [path, request] = api.POST.mock.calls[1];
	expect(path).toBe('/api/v1/schedule_configs');
	expect(request.body).toMatchObject({
		name: 'Hourly demo',
		task_func: 'hello_world',
		enabled: true
	});
	// Exactly one of the two triggers is sent.
	expect(
		[request.body.cron_expression, request.body.interval_seconds].filter((v) => v !== null)
	).toHaveLength(1);
});
