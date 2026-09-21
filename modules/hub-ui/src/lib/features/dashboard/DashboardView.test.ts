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
