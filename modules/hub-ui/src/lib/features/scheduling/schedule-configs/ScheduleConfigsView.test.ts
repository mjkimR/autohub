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

test.each(['cron', 'interval'] as const)(
	'editing switches to %s, clears the previous trigger and preserves the payload',
	async (target) => {
		const saved = {
			...config('s1', 'Nightly demo', 'hello_world'),
			cron_expression: target === 'interval' ? '0 6 * * *' : null,
			interval_seconds: target === 'cron' ? 600 : null,
			payload: { nested: { untouched: ['keep', 7] } }
		};
		api.GET.mockImplementation(async (path: string) =>
			path === '/api/v1/tasks/specs'
				? { data: [{ name: 'hello_world', payload_schema: null }] }
				: { data: { items: [saved] } }
		);
		api.PUT.mockResolvedValue({ data: saved });
		const user = userEvent.setup();
		render(ScheduleConfigsView);
		await screen.findByText('Nightly demo');
		await user.click(screen.getByTitle('Edit Schedule'));
		expect((screen.getByLabelText('Target Task') as HTMLInputElement).disabled).toBe(true);
		await user.click(
			screen.getByRole('button', {
				name: target === 'cron' ? 'Cron Expression' : 'Interval Seconds'
			})
		);
		if (target === 'cron') {
			await fireEvent.input(screen.getByLabelText('Cron Expression'), {
				target: { value: '0 12 * * *' }
			});
		} else {
			await fireEvent.input(screen.getByLabelText('Interval (Seconds)'), {
				target: { value: '120' }
			});
		}
		await user.click(screen.getByRole('button', { name: 'Save Changes' }));
		await waitFor(() =>
			expect(api.PUT).toHaveBeenCalledWith('/api/v1/schedule_configs/{schedule_config_id}', {
				params: { path: { schedule_config_id: 's1' } },
				body: {
					name: 'Nightly demo',
					description: null,
					task_func: 'hello_world',
					enabled: true,
					cron_expression: target === 'cron' ? '0 12 * * *' : null,
					interval_seconds: target === 'interval' ? 120 : null,
					payload: saved.payload
				}
			})
		);
		await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
	}
);

test('a managed schedule edit refusal keeps the editor and its input available', async () => {
	api.PUT.mockResolvedValue({ error: { detail: 'Edit this schedule from its project' } });
	const user = userEvent.setup();
	render(ScheduleConfigsView);
	await screen.findByText('Weekly audit');
	await user.click(screen.getAllByTitle('Edit Schedule')[1]);
	await fireEvent.input(screen.getByLabelText('Schedule Name'), {
		target: { value: 'Changed audit' }
	});
	await user.click(screen.getByRole('button', { name: 'Save Changes' }));
	await waitFor(() =>
		expect(toast.error).toHaveBeenCalledWith('Edit this schedule from its project')
	);
	expect((screen.getByLabelText('Schedule Name') as HTMLInputElement).value).toBe('Changed audit');
	expect((screen.getByRole('button', { name: 'Save Changes' }) as HTMLButtonElement).disabled).toBe(
		false
	);
});
