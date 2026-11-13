import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import ProjectExceptionStrip from '$lib/features/project-management/projects/ProjectExceptionStrip.svelte';
import AttentionView from './AttentionView.svelte';
import { OWED_KINDS } from './owed-kinds';
import { ITEM, PLAN, PROJECT, RUN, owedItem } from './owed-fixtures';
import type { OwedItem } from './owed-links';
import { OWED_COUNTS_CONTEXT, OwedCountsStore } from './owed-counts.svelte';

const { api, page, goto } = vi.hoisted(() => ({
	api: { GET: vi.fn() },
	page: { url: new URL('http://hub.test/') },
	goto: vi.fn()
}));
vi.mock('$lib/api', () => ({ api }));
vi.mock('$app/state', () => ({ page }));
vi.mock('$app/navigation', () => ({ goto }));

type Page = { items: OwedItem[]; has_more: boolean; next_cursor: string | null };
let pages: (query: Record<string, unknown>) => Promise<unknown>;

const pageOf = (items: OwedItem[], next: string | null = null): { data: Page } => ({
	data: { items, has_more: next !== null, next_cursor: next }
});

const everyKind = (): OwedItem[] => [
	owedItem('failed-run', { subject: { id: 'f1' }, context: { run_id: 'f1' } }),
	owedItem('connection-test-cleanup'),
	owedItem('sdd-batch-attention'),
	owedItem('work-item-attention', { context: { work_item_id: ITEM } }),
	owedItem('work-item-replacement', { context: { work_item_id: ITEM } }),
	owedItem('work-item-recovery', { context: { work_item_id: ITEM } }),
	owedItem('work-plan-proposed', { context: { work_plan_id: PLAN } }),
	owedItem('stopped-run', {
		subject: { id: RUN },
		context: {
			run_id: RUN,
			catalog_hold: {
				catalog_id: '66666666-6666-4666-8666-666666666666',
				reason: 'quota-blocked',
				available_at: '2026-11-12T12:00:00Z'
			}
		}
	}),
	owedItem('decision', { context: { run_id: RUN } })
];

beforeEach(() => {
	page.url = new URL('http://hub.test/');
	goto.mockReset();
	pages = async () => pageOf(everyKind());
	api.GET.mockReset();
	api.GET.mockImplementation(async (path: string, init?: { params?: { query?: object } }) => {
		if (path === '/api/v1/owed-items') return pages({ ...init?.params?.query });
		if (path === '/api/v1/projects')
			return { data: { items: [{ id: PROJECT, name: 'Application' }], total_count: 1 } };
		throw new Error(`unexpected ${path}`);
	});
});
afterEach(() => cleanup());

const groupOrder = () =>
	[...document.querySelectorAll('[data-owed-group]')].map((el) =>
		el.getAttribute('data-owed-group')
	);
const group = (kind: string) =>
	document.querySelector(`[data-owed-group="${kind}"]`) as HTMLElement;

test('groups every kind by consequence with failed runs last and quiet', async () => {
	render(AttentionView);
	await waitFor(() => expect(groupOrder()).toHaveLength(9));
	expect(groupOrder()).toEqual(OWED_KINDS.map((entry) => entry.kind));
	expect(group('decision').querySelector('[data-owed-count]')?.className).toContain('attention');
	const quiet = group('failed-run').querySelector('[data-owed-count]')!;
	expect(quiet.getAttribute('data-owed-count')).toBe('quiet');
	expect(quiet.className).not.toContain('attention');
	expect(within(group('failed-run')).getByText(/Not counted as owed/)).toBeTruthy();
	expect(screen.getByRole('heading', { level: 1, name: 'Attention' })).toBeTruthy();
});

test.each([
	['decision', 'Answer', `/projects/${PROJECT}/runs/${RUN}#decisions`],
	['stopped-run', 'Resume run', `/projects/${PROJECT}/runs/${RUN}`],
	['work-plan-proposed', 'Review plan', `/projects/${PROJECT}?tab=plans#work-plan-${PLAN}`],
	['work-item-recovery', 'Inspect recovery', `/projects/${PROJECT}?tab=plans#work-item-${ITEM}`],
	[
		'work-item-replacement',
		'Accept replacement',
		`/projects/${PROJECT}?tab=plans#work-item-${ITEM}`
	],
	['work-item-attention', 'Inspect Work Item', `/projects/${PROJECT}?tab=plans#work-item-${ITEM}`],
	['sdd-batch-attention', 'Inspect batch', `/projects/${PROJECT}?tab=repository`],
	['connection-test-cleanup', 'Review cleanup', `/projects/${PROJECT}?tab=connections`],
	['failed-run', 'Inspect run', `/projects/${PROJECT}/runs/f1#next-step`]
])(
	'%s row: cause, subject, project, waiting age and one action to its owner',
	async (kind, label, href) => {
		render(AttentionView);
		await waitFor(() => expect(group(kind)).toBeTruthy());
		const row = group(kind).querySelector('li')!;
		const actions = within(row).getAllByRole('link', { name: new RegExp(`^${label}`) });
		expect(actions).toHaveLength(1);
		expect(actions[0].getAttribute('href')).toBe(href);
		expect(within(row).getByText(`${label} cause`)).toBeTruthy();
		expect(within(row).getByText(`${kind} title`)).toBeTruthy();
		await waitFor(() =>
			expect(within(row).getByRole('link', { name: 'Application' }).getAttribute('href')).toBe(
				`/projects/${PROJECT}`
			)
		);
		expect(row.querySelector('time')?.getAttribute('datetime')).toBe('2026-11-12T06:30:00Z');
		expect(row.querySelector('time')?.textContent).toMatch(/^Waiting /);
	}
);

test('a catalog hold is inline context on the affected row only, never its own item', async () => {
	render(AttentionView);
	await waitFor(() => expect(group('stopped-run')).toBeTruthy());
	const holds = document.querySelectorAll('[data-catalog-hold]');
	expect(holds).toHaveLength(1);
	expect(group('stopped-run').contains(holds[0])).toBe(true);
	expect(holds[0].textContent).toContain('AI catalog quota is exhausted until');
	expect(holds[0].className).not.toContain('attention');
	expect(document.querySelector('[data-owed-group="catalog"]')).toBeNull();
});

test('a decision without a known run opens the inbox', async () => {
	pages = async () => pageOf([owedItem('decision')]);
	render(AttentionView);
	const link = await screen.findByRole('link', { name: /^Answer/ });
	expect(link.getAttribute('href')).toBe('/decisions');
});

test('only some kinds present renders only their groups', async () => {
	pages = async () => pageOf([owedItem('sdd-batch-attention'), owedItem('decision')]);
	render(AttentionView);
	await waitFor(() => expect(groupOrder()).toEqual(['decision', 'sdd-batch-attention']));
	expect(document.querySelector('[data-owed-empty]')).toBeNull();
});

test('empty shows "Nothing needs you" with a quiet link to PR runs', async () => {
	pages = async () => pageOf([]);
	render(AttentionView);
	expect(await screen.findByRole('heading', { name: 'Nothing needs you' })).toBeTruthy();
	expect(screen.getByRole('link', { name: 'Review PR runs' }).getAttribute('href')).toBe(
		'/projects/runs'
	);
	expect(document.querySelector('[data-owed-count]')).toBeNull();
});

test('failed runs alone still read "Nothing needs you" above the quiet section', async () => {
	pages = async () => pageOf([owedItem('failed-run')]);
	render(AttentionView);
	expect(await screen.findByRole('heading', { name: 'Nothing needs you' })).toBeTruthy();
	expect(groupOrder()).toEqual(['failed-run']);
});

test('loading shows a static skeleton with status text', async () => {
	pages = () => new Promise(() => {});
	render(AttentionView);
	expect(screen.getByRole('status').textContent).toContain('Loading what needs you');
	expect(document.querySelector('.animate-pulse')).toBeNull();
	expect(document.querySelector('[data-owed-empty]')).toBeNull();
});

test('an error shows a retry banner and keeps the last data', async () => {
	render(AttentionView);
	await waitFor(() => expect(groupOrder()).toHaveLength(9));
	pages = async () => ({ error: { detail: 'Owed items are unavailable' } });
	await fireEvent.click(screen.getByRole('button', { name: 'Refresh' }));
	const alert = await screen.findByRole('alert');
	expect(alert.textContent).toContain('Owed items are unavailable');
	expect(groupOrder()).toHaveLength(9);
	pages = async () => pageOf([owedItem('decision', { context: { run_id: RUN } })]);
	await fireEvent.click(within(alert).getByRole('button', { name: 'Retry' }));
	await waitFor(() => expect(groupOrder()).toEqual(['decision']));
	expect(screen.queryByRole('alert')).toBeNull();
});

test('a first-load error is not mistaken for "Nothing needs you"', async () => {
	pages = async () => Promise.reject(new Error('offline'));
	render(AttentionView);
	expect(await screen.findByRole('alert')).toBeTruthy();
	expect(screen.queryByText('Nothing needs you')).toBeNull();
	expect(document.querySelector('[data-owed-group]')).toBeNull();
});

test('Load more appends the next keyset page with the cursor and the page limit', async () => {
	pages = async (query) =>
		query.cursor === 'c2'
			? pageOf([owedItem('connection-test-cleanup')])
			: pageOf([owedItem('decision', { context: { run_id: RUN } })], 'c2');
	render(AttentionView);
	await waitFor(() => expect(groupOrder()).toEqual(['decision']));
	expect(screen.getByText(/Showing the 1 longest-waiting items/)).toBeTruthy();
	await fireEvent.click(screen.getByRole('button', { name: 'Load more' }));
	await waitFor(() => expect(groupOrder()).toEqual(['decision', 'connection-test-cleanup']));
	expect(screen.queryByRole('button', { name: 'Load more' })).toBeNull();
	expect(api.GET).toHaveBeenCalledWith('/api/v1/owed-items', {
		params: { query: { limit: 100 } }
	});
	expect(api.GET).toHaveBeenCalledWith('/api/v1/owed-items', {
		params: { query: { limit: 100, cursor: 'c2' } }
	});
});

test('choosing a project restarts the list with that filter', async () => {
	render(AttentionView);
	await waitFor(() => expect(groupOrder()).toHaveLength(9));
	await screen.findByRole('option', { name: 'Application' });
	pages = async () => pageOf([]);
	await fireEvent.change(screen.getByRole('combobox', { name: 'Project' }), {
		target: { value: PROJECT }
	});
	expect(
		await screen.findByRole('heading', { name: 'Nothing needs you in this project' })
	).toBeTruthy();
	expect(api.GET).toHaveBeenCalledWith('/api/v1/owed-items', {
		params: { query: { limit: 100, project_id: PROJECT } }
	});
	expect(goto).toHaveBeenCalledWith(
		`/?project=${PROJECT}`,
		expect.objectContaining({ replaceState: true })
	);
	await fireEvent.click(screen.getByRole('button', { name: 'Show all projects' }));
	expect(goto).toHaveBeenLastCalledWith('/', expect.objectContaining({ replaceState: true }));
});

test('?project= on the URL is the initial filter, with one read', async () => {
	page.url = new URL(`http://hub.test/?project=${PROJECT}`);
	pages = async () => pageOf([owedItem('decision', { context: { run_id: RUN } })]);
	render(AttentionView);
	await waitFor(() => expect(groupOrder()).toEqual(['decision']));
	const reads = api.GET.mock.calls.filter(([path]) => path === '/api/v1/owed-items');
	expect(reads).toEqual([
		['/api/v1/owed-items', { params: { query: { limit: 100, project_id: PROJECT } } }]
	]);
	await waitFor(() =>
		expect((screen.getByRole('combobox', { name: 'Project' }) as HTMLSelectElement).value).toBe(
			PROJECT
		)
	);
});

test("the project strip's View in Attention link round-trips to the filtered landing", async () => {
	const counts = vi.fn(async () => ({
		data: { total: 1, by_kind: { decision: 1 }, by_project: { [PROJECT]: 1 } }
	}));
	const listing = api.GET.getMockImplementation()!;
	api.GET.mockImplementation(async (path: string, init?: { params?: { query?: object } }) =>
		path === '/api/v1/owed-items/counts' ? counts() : listing(path, init)
	);
	render(ProjectExceptionStrip, { projectId: PROJECT });
	const link = await screen.findByRole('link', { name: 'View in Attention' });
	const href = link.getAttribute('href')!;
	cleanup();

	page.url = new URL(href, 'http://hub.test');
	pages = async () => pageOf([owedItem('decision', { context: { run_id: RUN } })]);
	render(AttentionView);
	await waitFor(() => expect(groupOrder()).toEqual(['decision']));
	expect(api.GET).toHaveBeenCalledWith('/api/v1/owed-items', {
		params: { query: { limit: 100, project_id: PROJECT } }
	});
	await waitFor(() =>
		expect((screen.getByRole('combobox', { name: 'Project' }) as HTMLSelectElement).value).toBe(
			PROJECT
		)
	);
});

test('shell counts size the groups and summary without another read', async () => {
	const store = new OwedCountsStore();
	store.value = {
		status: 'known',
		total: 12,
		byKind: { decision: 5, 'failed-run': 3 },
		byProject: { [PROJECT]: 12 }
	};
	pages = async () => pageOf([owedItem('decision', { context: { run_id: RUN } })], 'c2');
	render(AttentionView, { context: new Map([[OWED_COUNTS_CONTEXT, store]]) });
	await waitFor(() => expect(groupOrder()).toEqual(['decision']));
	expect(group('decision').querySelector('[data-owed-count]')?.textContent).toContain('5');
	expect(within(group('decision')).getByText('1 shown')).toBeTruthy();
	expect(screen.getByText('12 items need you.')).toBeTruthy();
	expect(api.GET).not.toHaveBeenCalledWith('/api/v1/owed-items/counts', expect.anything());
	expect(api.GET).not.toHaveBeenCalledWith('/api/v1/owed-items/counts');
});
