import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, expect, test, vi } from 'vitest';
import ScheduleJobsView from './ScheduleJobsView.svelte';

const { api } = vi.hoisted(() => ({ api: { GET: vi.fn() } }));

vi.mock('$lib/api', () => ({ api }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

const job = (id: string, name: string, status: string, error_message: string | null = null) => ({
	id,
	name,
	status,
	error_message,
	schedule_config_id: null,
	dispatcher_run_id: id === 'j3' ? null : 'run-1',
	started_at: '2026-09-21T00:00:00Z',
	finished_at: status === 'pending' ? null : '2026-09-21T00:00:05Z',
	payload: {},
	retry_need: false,
	retry_attempts: 1,
	retry_max: 3,
	created_at: '2026-09-21T00:00:00Z',
	updated_at: '2026-09-21T00:00:05Z'
});

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

test('lists jobs with why one failed and filters by name or status', async () => {
	api.GET.mockResolvedValue({
		data: {
			total_count: 3,
			items: [
				job('j1', 'Application dispatch', 'success'),
				job(
					'j2',
					'Jules sync',
					'failure',
					'GitHubObservationError: GitHub merge returned HTTP 500'
				),
				job('j3', 'Manual check', 'pending')
			]
		}
	});
	render(ScheduleJobsView);

	expect(await screen.findByText('Application dispatch')).toBeTruthy();
	expect(screen.getByText(/GitHub merge returned HTTP 500/)).toBeTruthy();
	expect(screen.getByText('manual')).toBeTruthy();

	api.GET.mockResolvedValue({
		data: { items: [job('j2', 'Jules sync', 'failure')], total_count: 1 }
	});
	await fireEvent.input(screen.getByPlaceholderText('Filter jobs by name or status...'), {
		target: { value: 'FAIL' }
	});
	await waitFor(() => expect(screen.queryByText('Application dispatch')).toBeNull());
	expect(api.GET).toHaveBeenLastCalledWith('/api/v1/schedule_jobs', {
		params: {
			query: { search: 'FAIL', status: undefined, offset: 0, limit: 50, skip_count: false }
		}
	});
	expect(screen.getByText('Jules sync')).toBeTruthy();
});

test('says so when nothing has run', async () => {
	api.GET.mockResolvedValue({ data: { items: [], total_count: 0 } });
	render(ScheduleJobsView);
	expect(await screen.findByText('No execution logs recorded')).toBeTruthy();
});

test('pages through jobs, sends filters to the server and retries a failed page', async () => {
	api.GET.mockImplementation(async (_path, options) => {
		const query = options.params.query;
		const last = query.offset > 0;
		return {
			data: {
				items: [job(last ? 'j51' : 'j1', last ? 'Old job' : 'Recent job', 'success')],
				total_count: 51
			}
		};
	});
	render(ScheduleJobsView);
	await screen.findByText('Recent job');
	await fireEvent.click(screen.getByRole('button', { name: 'Next page' }));
	expect(await screen.findByText('Old job')).toBeTruthy();
	await fireEvent.change(screen.getByRole('combobox', { name: 'Job status' }), {
		target: { value: 'failure' }
	});
	await waitFor(() =>
		expect(api.GET).toHaveBeenLastCalledWith('/api/v1/schedule_jobs', {
			params: { query: { offset: 0, limit: 50, search: '', status: 'failure', skip_count: false } }
		})
	);
	api.GET.mockResolvedValue({ error: { detail: 'Unavailable' } });
	await fireEvent.click(screen.getByRole('button', { name: 'Refresh' }));
	await screen.findByRole('alert');
	expect(screen.queryByText('No execution logs recorded')).toBeNull();
	api.GET.mockResolvedValue({
		data: { items: [job('recovered', 'Recovered job', 'failure')], total_count: 1 }
	});
	await fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
	expect(await screen.findByText('Recovered job')).toBeTruthy();
});
