import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import DashboardView from './DashboardView.svelte';

const { api } = vi.hoisted(() => ({ api: { GET: vi.fn() } }));

vi.mock('$lib/api', () => ({ api }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

const run = (id: string, state: string) => ({
	id,
	project_id: 'p1',
	state,
	pull_number: Number(id.slice(1)),
	pull_url: `https://github.com/owner/app/pull/${id.slice(1)}`,
	branch: `feature/${id}`,
	pause_reason: null,
	revision: 1,
	created_at: '2026-09-21T00:00:00Z',
	updated_at: '2026-09-21T00:00:00Z'
});

let deepHealth: Record<string, unknown>;

beforeEach(() => {
	deepHealth = {
		status: 'ok',
		database: 'connected',
		scheduler: 'ok',
		last_tick_at: '2026-09-21T00:00:00Z'
	};
	api.GET.mockImplementation(async (path: string) => {
		if (path === '/api/v1/dashboard/stats')
			return {
				data: {
					project_count: 1,
					schedule_count: 0,
					connector_count: 2,
					active_connector_count: 1,
					total_runs: 6,
					runs_by_state: {
						implementing: 1,
						awaiting_ci: 1,
						completed: 1,
						failed: 1,
						paused: 1,
						blocked: 1
					}
				}
			};
		if (path === '/api/health') return { data: { status: 'ok' } };
		if (path === '/api/health/deep') return { data: deepHealth };
		if (path === '/api/v1/projects')
			return { data: { items: [{ id: 'p1', name: 'Application' }], total_count: 1 } };
		if (path === '/api/v1/pipeline-runs')
			return {
				data: {
					items: [
						run('r1', 'implementing'),
						run('r2', 'awaiting_ci'),
						run('r3', 'completed'),
						run('r4', 'failed'),
						run('r5', 'paused'),
						run('r6', 'blocked')
					],
					total_count: 6
				}
			};
		if (path === '/api/v1/connectors')
			return {
				data: {
					items: [
						{ id: 'c1', enabled: true },
						{ id: 'c2', enabled: false }
					],
					total_count: 2
				}
			};
		return { data: { items: [], total_count: 0 } };
	});
});

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

const tile = (label: string) => screen.getByText(label).parentElement as HTMLElement;

test('counts runs by where they stand, including every state that waits for the operator', async () => {
	render(DashboardView);

	await waitFor(() => expect(tile('Total Runs').textContent).toContain('6'));
	expect(tile('Active Work').textContent).toContain('1');
	expect(tile('Awaiting CI').textContent).toContain('1');
	expect(tile('Completed').textContent).toContain('1');
	// failed + paused + blocked
	expect(tile('Needs you').textContent).toContain('3');
	expect(screen.getByText('Operational')).toBeTruthy();
	expect(screen.getByText('Connected')).toBeTruthy();
	expect(screen.getByText('Firing')).toBeTruthy();
});

test('a scheduler trigger that stopped is shown even though the API answers', async () => {
	deepHealth = { ...deepHealth, scheduler: 'stale' };
	render(DashboardView);

	expect(await screen.findByText('Stopped')).toBeTruthy();
	expect(screen.getByText('Operational')).toBeTruthy();
});

test('an unreachable backend is reported as unavailable', async () => {
	api.GET.mockRejectedValue(new Error('offline'));
	render(DashboardView);

	expect(await screen.findByText('Unavailable')).toBeTruthy();
	expect(screen.getByText('Disconnected')).toBeTruthy();
});

test('statistics come from the full history even when only five recent runs are shown', async () => {
	const previous = api.GET.getMockImplementation()!;
	api.GET.mockImplementation(async (path: string, ...args: unknown[]) => {
		if (path === '/api/v1/dashboard/stats')
			return {
				data: {
					project_count: 51,
					schedule_count: 101,
					connector_count: 102,
					active_connector_count: 101,
					total_runs: 151,
					runs_by_state: { completed: 150, blocked: 1 }
				}
			};
		return previous(path, ...args);
	});
	render(DashboardView);
	await waitFor(() => expect(tile('Total Runs').textContent).toContain('151'));
	expect(tile('Completed').textContent).toContain('150');
	expect(tile('Needs you').textContent).toContain('1');
	expect(screen.getByText(/101 active connectors/)).toBeTruthy();
});

test('HTTP failure shows unavailable statistics instead of a zero total', async () => {
	api.GET.mockResolvedValue({ error: { detail: 'Unavailable' } });
	render(DashboardView);
	expect(await screen.findByRole('alert')).toBeTruthy();
	expect(tile('Total Runs').textContent).toContain('—');
});

const withRunsByState = (runsByState: Record<string, number> | null) => {
	const previous = api.GET.getMockImplementation()!;
	api.GET.mockImplementation(async (path: string, ...args: unknown[]) => {
		if (path === '/api/v1/dashboard/stats') {
			if (!runsByState) return { error: { detail: 'Unavailable' } };
			const result = await previous(path, ...args);
			return { data: { ...result.data, runs_by_state: runsByState } };
		}
		return previous(path, ...args);
	});
};

test('runs waiting for the operator mark the Needs-you tile and link to Pipeline Runs', async () => {
	withRunsByState({ completed: 3, failed: 1, paused: 2, blocked: 1 });
	render(DashboardView);

	const link = await screen.findByRole('link', { name: /Needs you/ });
	expect(link.getAttribute('href')).toBe('/projects/runs');
	expect(link.getAttribute('data-attention')).toBe('true');
	expect(link.textContent).toContain('4');
	expect(link.textContent).toContain('1 failed · 2 paused · 1 blocked');
	expect(document.querySelectorAll('[data-attention="true"]')).toHaveLength(1);
});

test('the breakdown lists only the states that have runs', async () => {
	withRunsByState({ paused: 2 });
	render(DashboardView);

	const link = await screen.findByRole('link', { name: /Needs you/ });
	expect(link.textContent).toContain('2 paused');
	expect(link.textContent).not.toContain('failed ·');
	expect(link.textContent).not.toContain('blocked');
});

test('with nothing failed or held the Needs-you tile is neutral and not a link', async () => {
	withRunsByState({ completed: 4 });
	render(DashboardView);

	await waitFor(() => expect(tile('Needs you').textContent).toContain('No failed or held runs'));
	expect(tile('Needs you').textContent).toContain('Failed, paused, or blocked');
	expect(screen.queryByRole('link', { name: /Needs you/ })).toBeNull();
	expect(document.querySelector('[data-attention]')).toBeNull();
});

test('unavailable statistics keep the Needs-you tile neutral with the unknown marker', async () => {
	withRunsByState(null);
	render(DashboardView);

	await waitFor(() => expect(tile('Needs you').textContent).toContain('—'));
	expect(tile('Needs you').textContent).toContain('Failed, paused, or blocked');
	expect(screen.queryByRole('link', { name: /Needs you/ })).toBeNull();
	expect(document.querySelector('[data-attention]')).toBeNull();
});
