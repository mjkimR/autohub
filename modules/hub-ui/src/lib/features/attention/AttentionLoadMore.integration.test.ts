import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import AttentionView from './AttentionView.svelte';
import { PROJECT, RUN, owedItem } from './owed-fixtures';

const { api, page, goto } = vi.hoisted(() => ({
	api: { GET: vi.fn() },
	page: { url: new URL('http://hub.test/') },
	goto: vi.fn()
}));
vi.mock('$lib/api', () => ({ api }));
vi.mock('$app/state', () => ({ page }));
vi.mock('$app/navigation', () => ({ goto }));

type Query = { cursor?: string; project_id?: string };
/** Cursor reads wait here until the test releases them, so a Load more stays in flight. */
let held: ((value: unknown) => void)[];

const firstPage = () => ({
	data: {
		items: [owedItem('decision', { context: { run_id: RUN } })],
		has_more: true,
		next_cursor: 'c2'
	}
});
const lastPage = {
	data: { items: [owedItem('connection-test-cleanup')], has_more: false, next_cursor: null }
};

beforeEach(() => {
	page.url = new URL('http://hub.test/');
	held = [];
	api.GET.mockReset();
	api.GET.mockImplementation(async (path: string, init?: { params?: { query?: Query } }) => {
		if (path === '/api/v1/projects')
			return { data: { items: [{ id: PROJECT, name: 'Application' }], total_count: 1 } };
		if (path !== '/api/v1/owed-items') throw new Error(`unexpected ${path}`);
		if (init?.params?.query?.cursor) return new Promise((resolve) => held.push(resolve));
		return firstPage();
	});
});
afterEach(() => cleanup());

const cursorReads = () =>
	api.GET.mock.calls.filter(
		([path, init]) => path === '/api/v1/owed-items' && init?.params?.query?.cursor
	);
const loadMore = () => screen.getByRole('button', { name: /^(Load more|Loading…)$/ });

async function startLoadMore() {
	await screen.findByRole('button', { name: 'Load more' });
	await fireEvent.click(loadMore());
	await waitFor(() => expect(loadMore().textContent).toContain('Loading…'));
	expect(cursorReads()).toHaveLength(1);
}

async function expectLoadMoreWorks(query: Query) {
	// The discarded page lands late and must not leave the button stuck.
	held[0](lastPage);
	await waitFor(() => expect((loadMore() as HTMLButtonElement).disabled).toBe(false));
	expect(loadMore().textContent).toContain('Load more');
	await fireEvent.click(loadMore());
	await waitFor(() => expect(cursorReads()).toHaveLength(2));
	expect(cursorReads()[1][1]).toEqual({ params: { query: { limit: 100, ...query } } });
	held[1](lastPage);
	await waitFor(() =>
		expect(document.querySelector('[data-owed-group="connection-test-cleanup"]')).toBeTruthy()
	);
	expect(screen.queryByRole('button', { name: /^(Load more|Loading…)$/ })).toBeNull();
}

test('Refresh during Load more leaves Load more working afterwards', async () => {
	render(AttentionView);
	await startLoadMore();
	await fireEvent.click(screen.getByRole('button', { name: 'Refresh' }));
	await waitFor(() =>
		expect(api.GET.mock.calls.filter(([path]) => path === '/api/v1/owed-items')).toHaveLength(3)
	);
	await expectLoadMoreWorks({ cursor: 'c2' });
	// The stale page was discarded rather than appended twice.
	expect(document.querySelectorAll('[data-owed-group="connection-test-cleanup"] li')).toHaveLength(
		1
	);
});

test('a project change during Load more leaves Load more working afterwards', async () => {
	render(AttentionView);
	await screen.findByRole('option', { name: 'Application' });
	await startLoadMore();
	await fireEvent.change(screen.getByRole('combobox', { name: 'Project' }), {
		target: { value: PROJECT }
	});
	await waitFor(() =>
		expect(api.GET).toHaveBeenCalledWith('/api/v1/owed-items', {
			params: { query: { limit: 100, project_id: PROJECT } }
		})
	);
	await expectLoadMoreWorks({ cursor: 'c2', project_id: PROJECT });
});
