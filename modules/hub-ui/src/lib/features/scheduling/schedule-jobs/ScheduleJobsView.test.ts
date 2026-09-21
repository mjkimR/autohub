import { cleanup, fireEvent, render, screen } from '@testing-library/svelte';
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

	await fireEvent.input(screen.getByPlaceholderText('Filter jobs by name or status...'), {
		target: { value: 'FAIL' }
	});
	expect(screen.queryByText('Application dispatch')).toBeNull();
	expect(screen.getByText('Jules sync')).toBeTruthy();
});

test('says so when nothing has run', async () => {
	api.GET.mockResolvedValue({ data: { items: [] } });
	render(ScheduleJobsView);
	expect(await screen.findByText('No execution logs recorded')).toBeTruthy();
});
