import { cleanup, render, screen, waitFor, within } from '@testing-library/svelte';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import ProjectDetailView from './ProjectDetailView.svelte';
import { owedChips } from './owed-signals';

const { api } = vi.hoisted(() => ({
	api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() }
}));
vi.mock('$lib/api', () => ({ api }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn(), success: vi.fn(), warning: vi.fn() } }));

const project = {
	id: 'p1',
	name: 'Application',
	project_type: 'general',
	enabled: true,
	revision: 4,
	github: null,
	last_check: null,
	created_at: '2026-09-22T00:00:00Z',
	updated_at: '2026-09-22T00:00:00Z'
};
const zero = {
	decision: 0,
	'stopped-run': 0,
	'work-plan-proposed': 0,
	'work-item-recovery': 0,
	'work-item-replacement': 0,
	'work-item-attention': 0,
	'sdd-batch-attention': 0,
	'connection-test-cleanup': 0,
	'failed-run': 0
};
let counts: () => Promise<{ data?: unknown; error?: unknown }>;

function countCalls() {
	return api.GET.mock.calls.filter(([path]) => path === '/api/v1/owed-items/counts');
}
function strip() {
	const element = document.getElementById('needs-you');
	if (!element) throw new Error('No exception strip yet');
	return element;
}

beforeEach(() => {
	counts = async () => ({ data: { total: 0, by_kind: zero, by_project: {} } });
	api.GET.mockImplementation(async (path: string) => {
		if (path === '/api/v1/owed-items/counts') return counts();
		if (path === '/api/v1/projects/{project_id}') return { data: project };
		if (path === '/api/v1/ai-catalogs') return { data: { items: [] } };
		return { data: { items: [], total_count: 0 } };
	});
});
afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

test('populated strip shows one chip per kind linking to where it is resolved', async () => {
	counts = async () => ({
		data: {
			total: 7,
			by_kind: {
				...zero,
				decision: 2,
				'stopped-run': 1,
				'work-plan-proposed': 1,
				'work-item-recovery': 1,
				'sdd-batch-attention': 1,
				'connection-test-cleanup': 1,
				'failed-run': 3
			},
			by_project: { p1: 7 }
		}
	});
	render(ProjectDetailView, { projectId: 'p1', tab: 'overview' });
	const decisions = await screen.findByRole('link', { name: /2 decisions/ });
	const region = within(strip());
	const href = (name: string) => region.getByRole('link', { name }).getAttribute('href');
	expect(decisions.getAttribute('href')).toBe('/projects/p1?tab=runs');
	expect(href('1 held PR run')).toBe('/projects/p1?tab=runs');
	expect(href('1 Work Plan to review')).toBe('/projects/p1?tab=plans');
	expect(href('1 Work Item recovery')).toBe('/projects/p1?tab=plans');
	expect(href('1 SDD batch in attention')).toBe('/projects/p1?tab=repository');
	expect(href('1 connection-test cleanup')).toBe('/projects/p1?tab=connections');
	expect(href('View in Attention')).toBe('/?project=p1');
	// Failed runs are listed quietly: outline chip, never the attention variant.
	const failed = region.getByRole('link', { name: '3 failed PR runs' });
	expect(failed.getAttribute('href')).toBe('/projects/p1?tab=runs');
	expect(failed.className).not.toContain('attention');
	expect(decisions.className).toContain('attention');
	expect(region.queryByText('No exceptions')).toBeNull();
	expect(countCalls()).toHaveLength(1);
	expect(countCalls()[0][1]).toEqual({ params: { query: { project_id: 'p1' } } });
});

test('every counted kind maps to a project section and a readable label', () => {
	const byKind = Object.fromEntries(Object.keys(zero).map((kind) => [kind, 1]));
	const chips = owedChips('p1', byKind);
	expect(chips.map((chip) => [chip.label, chip.href.split('?')[1], chip.quiet])).toEqual([
		['1 decision', 'tab=runs', false],
		['1 held PR run', 'tab=runs', false],
		['1 Work Plan to review', 'tab=plans', false],
		['1 Work Item recovery', 'tab=plans', false],
		['1 Work Item replacement', 'tab=plans', false],
		['1 Work Item needing attention', 'tab=plans', false],
		['1 SDD batch in attention', 'tab=repository', false],
		['1 connection-test cleanup', 'tab=connections', false],
		['1 failed PR run', 'tab=runs', true]
	]);
});

test('a clear project says so and offers no Attention link', async () => {
	render(ProjectDetailView, { projectId: 'p1', tab: 'overview' });
	expect(await within(await waitFor(strip)).findByText('No exceptions')).toBeTruthy();
	expect(screen.queryByRole('link', { name: 'View in Attention' })).toBeNull();
});

test('only failed runs show the quiet chip without claiming no exceptions', async () => {
	counts = async () => ({
		data: { total: 0, by_kind: { ...zero, 'failed-run': 1 }, by_project: {} }
	});
	render(ProjectDetailView, { projectId: 'p1', tab: 'overview' });
	expect(await screen.findByRole('link', { name: '1 failed PR run' })).toBeTruthy();
	expect(screen.queryByText('No exceptions')).toBeNull();
	expect(screen.queryByRole('link', { name: 'View in Attention' })).toBeNull();
});

test('loading hides counts and never shows zero', async () => {
	counts = () => new Promise(() => {});
	render(ProjectDetailView, { projectId: 'p1', tab: 'overview' });
	await waitFor(() => expect(strip().dataset.owedState).toBe('loading'));
	expect(within(strip()).getByRole('status').textContent).toBe('Checking…');
	expect(within(strip()).queryByText(/0/)).toBeNull();
	expect(within(strip()).queryByText('No exceptions')).toBeNull();
});

test('an unavailable count is a neutral dash with the reason', async () => {
	counts = async () => ({ error: { detail: 'Database busy' } });
	render(ProjectDetailView, { projectId: 'p1', tab: 'overview' });
	await waitFor(() => expect(strip().dataset.owedState).toBe('error'));
	const unknown = strip().querySelector('[data-owed-unknown]') as HTMLElement;
	expect(unknown.title).toBe('Needs-you counts unavailable: Database busy');
	expect(unknown.textContent).toContain('—');
	expect(strip().querySelector('[data-owed-kind]')).toBeNull();
	expect(within(strip()).queryByText('No exceptions')).toBeNull();
});

test('changing section re-reads the counts once, without polling', async () => {
	const view = render(ProjectDetailView, { projectId: 'p1', tab: 'overview' });
	await within(await waitFor(strip)).findByText('No exceptions');
	expect(countCalls()).toHaveLength(1);
	counts = async () => ({
		data: { total: 1, by_kind: { ...zero, 'work-plan-proposed': 1 }, by_project: { p1: 1 } }
	});
	await view.rerender({ projectId: 'p1', tab: 'plans' });
	expect(await screen.findByRole('link', { name: '1 Work Plan to review' })).toBeTruthy();
	expect(countCalls()).toHaveLength(2);
});
