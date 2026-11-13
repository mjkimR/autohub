import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import AppShell from './AppShell.svelte';

const { api, page } = vi.hoisted(() => ({
	api: { GET: vi.fn() },
	page: { url: new URL('http://hub.test/decisions') }
}));
vi.mock('$lib/api', () => ({ api }));
vi.mock('$lib/api/client', () => ({ logoutSession: vi.fn() }));
vi.mock('$app/state', () => ({ page }));

let decisions: () => Promise<unknown>;
let admin = false;

beforeEach(() => {
	admin = false;
	localStorage.clear();
	page.url = new URL('http://hub.test/decisions');
	decisions = async () => ({ data: decisionPage(0) });
	api.GET.mockReset();
	api.GET.mockImplementation(async (path: string) => {
		if (path === '/api/health') return { data: { status: 'ok' } };
		if (path === '/api/v1/users/me') return { data: { is_superadmin: admin } };
		if (path === '/api/v1/pipeline-runs/decisions') return decisions();
		throw new Error(`unexpected ${path}`);
	});
});
afterEach(() => cleanup());

const children = createRawSnippet(() => ({ render: () => '<p>content</p>' }));
const nav = () => screen.getByRole('navigation', { name: 'Primary navigation' });
const rules = () => document.querySelectorAll('[data-pending-rule]');
const decisionPage = (count: number, items: unknown[] = []) => ({
	items,
	has_more: count > items.length,
	next_cursor: count > items.length ? 'next' : null,
	actionable_total_count: count
});

test('the active item carries aria-current and the ink outline, others do not', async () => {
	render(AppShell, { children });
	const active = within(nav()).getByRole('link', { name: /Decisions/ });
	expect(active.getAttribute('aria-current')).toBe('page');
	expect(active.className).toContain('inset-ring-sidebar-ring');
	expect(active.className).not.toMatch(/border-l|attention/);
	const other = within(nav()).getByRole('link', { name: 'Projects' });
	expect(other.getAttribute('aria-current')).toBeNull();
	expect(other.className).not.toContain('inset-ring-sidebar-ring');
});

test('administrative links use the same active style', async () => {
	admin = true;
	page.url = new URL('http://hub.test/admin/machines');
	render(AppShell, { children });
	const link = await within(nav()).findByRole('link', { name: 'Machine keys' });
	expect(link.getAttribute('aria-current')).toBe('page');
	expect(link.className).toContain('inset-ring-sidebar-ring');
	const other = within(nav()).getByRole('link', { name: 'Account approval' });
	expect(other.getAttribute('aria-current')).toBeNull();
});

test('owed decisions light the top rule and label the Decisions count', async () => {
	decisions = async () => ({ data: decisionPage(2, [{ actionable: true }]) });
	render(AppShell, { children });
	const link = await within(nav()).findByRole('link', { name: 'Decisions 2 pending decisions' });
	expect(within(link).getByText('2')).toBeTruthy();
	expect(rules()).toHaveLength(2);
	expect(
		screen.getByRole('link', { name: 'Decisions: 2 pending decisions' }).getAttribute('href')
	).toBe('/decisions');
	expect(api.GET).toHaveBeenCalledWith('/api/v1/pipeline-runs/decisions', {
		params: { query: { limit: 1 } }
	});
});

test('a backlog beyond the read page is shown exactly', async () => {
	decisions = async () => ({ data: decisionPage(137, [{ actionable: false }]) });
	render(AppShell, { children });
	await within(nav()).findByRole('link', { name: 'Decisions 137 pending decisions' });
	expect(screen.getByText('137 pending')).toBeTruthy();
	expect(screen.queryByText(/\+/)).toBeNull();
});

test('zero stays fully neutral with no badge', async () => {
	decisions = async () => ({ data: decisionPage(0, [{ actionable: false }]) });
	render(AppShell, { children });
	await waitFor(() =>
		expect(api.GET).toHaveBeenCalledWith('/api/v1/pipeline-runs/decisions', expect.anything())
	);
	await new Promise((resolve) => setTimeout(resolve, 0));
	expect(within(nav()).getByRole('link', { name: 'Decisions' })).toBeTruthy();
	expect(rules()).toHaveLength(0);
	expect(document.querySelector('[data-pending-count]')).toBeNull();
	expect(document.querySelector('[data-pending-unknown]')).toBeNull();
	expect(screen.queryByRole('link', { name: /Decisions: / })).toBeNull();
});

test.each([
	['error', async () => ({ error: { detail: 'down' } })],
	['failure', async () => Promise.reject(new Error('offline'))],
	['invalid count', async () => ({ data: { items: [], has_more: false, next_cursor: null } })],
	['loading', () => new Promise(() => {})]
])('%s shows a neutral unknown mark, not zero or debt', async (_name, response) => {
	decisions = response;
	render(AppShell, { children });
	await waitFor(() =>
		expect(api.GET).toHaveBeenCalledWith('/api/v1/pipeline-runs/decisions', expect.anything())
	);
	await new Promise((resolve) => setTimeout(resolve, 0));
	const link = within(nav()).getByRole('link', { name: 'Decisions Pending decisions unknown' });
	const mark = link.querySelector('[data-pending-unknown]')!;
	expect(mark.textContent).toContain('?');
	expect(mark.getAttribute('title')).toBe('Pending decisions unknown');
	expect(mark.className).not.toContain('attention');
	const narrow = screen.getByRole('link', { name: 'Decisions: Pending decisions unknown' });
	expect(narrow.getAttribute('href')).toBe('/decisions');
	expect(narrow.getAttribute('title')).toBe('Pending decisions unknown');
	expect(narrow.innerHTML).not.toContain('attention');
	expect(rules()).toHaveLength(0);
	expect(document.querySelector('[data-pending-count]')).toBeNull();
});

test('the PR run list is labeled with the glossary term', () => {
	render(AppShell, { children });
	expect(within(nav()).getByRole('link', { name: 'PR runs' }).getAttribute('href')).toBe(
		'/projects/runs'
	);
	expect(within(nav()).queryByRole('link', { name: 'Pipeline runs' })).toBeNull();
});

const groupLabels = () =>
	[...nav().querySelectorAll('[data-nav-group]')].map((group) =>
		group.getAttribute('data-nav-group')
	);
const systemToggle = () => within(nav()).getByRole('button', { name: /^System/ });
const systemList = () => document.getElementById('nav-group-system')!;

test('destinations are grouped by operator job, administration last', async () => {
	admin = true;
	render(AppShell, { children });
	await within(nav()).findByRole('link', { name: 'Account approval' });
	expect(groupLabels()).toEqual(['attention', 'work', 'setup', 'system', 'admin']);
	const names = (id: string) =>
		[...document.querySelectorAll(`[data-nav-group="${id}"] a`)].map(
			(a) => a.querySelector('span')?.textContent
		);
	expect(names('attention')).toEqual(['Dashboard', 'Decisions']);
	expect(names('work')).toEqual(['Projects', 'PR runs']);
	expect(names('setup')).toEqual(['Connectors', 'AI catalogs', 'Notifications']);
	expect(names('system')).toEqual([
		'Schedule configs',
		'Schedule jobs',
		'Webhook deliveries',
		'Task specs',
		'System configs'
	]);
	expect(within(nav()).getByRole('group', { name: 'Work' })).toBeTruthy();
});

test('System starts collapsed with an accessible disclosure button', () => {
	page.url = new URL('http://hub.test/projects');
	render(AppShell, { children });
	const toggle = systemToggle();
	expect(toggle.getAttribute('aria-expanded')).toBe('false');
	expect(toggle.getAttribute('aria-controls')).toBe('nav-group-system');
	expect(systemList().hidden).toBe(true);
	expect(within(nav()).queryByRole('link', { name: 'Schedule jobs' })).toBeNull();
	expect(document.querySelector('[data-holds-current]')).toBeNull();
});

test('a System route opens the group and marks its link active', () => {
	page.url = new URL('http://hub.test/schedules/jobs');
	render(AppShell, { children });
	expect(systemToggle().getAttribute('aria-expanded')).toBe('true');
	const link = within(nav()).getByRole('link', { name: 'Schedule jobs' });
	expect(link.getAttribute('aria-current')).toBe('page');
	expect(screen.getAllByText('Schedule jobs').length).toBeGreaterThan(1);
});

test('collapsing over the current page keeps it discoverable', async () => {
	page.url = new URL('http://hub.test/operations/tasks');
	render(AppShell, { children });
	await fireEvent.click(systemToggle());
	expect(systemToggle().getAttribute('aria-expanded')).toBe('false');
	expect(systemList().hidden).toBe(true);
	expect(systemToggle().textContent).toContain('contains the current page');
	expect(document.querySelector('[data-holds-current]')).toBeTruthy();
});

test('the System open state is remembered per browser', async () => {
	page.url = new URL('http://hub.test/projects');
	render(AppShell, { children });
	await fireEvent.click(systemToggle());
	expect(systemToggle().getAttribute('aria-expanded')).toBe('true');
	expect(localStorage.getItem('autohub.nav.system.open')).toBe('true');
	cleanup();
	render(AppShell, { children });
	expect(systemToggle().getAttribute('aria-expanded')).toBe('true');
	await fireEvent.click(systemToggle());
	expect(localStorage.getItem('autohub.nav.system.open')).toBe('false');
	cleanup();
	render(AppShell, { children });
	expect(systemToggle().getAttribute('aria-expanded')).toBe('false');
});

test('unavailable storage falls back to collapsed and still toggles', async () => {
	const get = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
		throw new Error('blocked');
	});
	const set = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
		throw new Error('blocked');
	});
	try {
		page.url = new URL('http://hub.test/projects');
		render(AppShell, { children });
		expect(systemToggle().getAttribute('aria-expanded')).toBe('false');
		await fireEvent.click(systemToggle());
		expect(systemToggle().getAttribute('aria-expanded')).toBe('true');
	} finally {
		get.mockRestore();
		set.mockRestore();
	}
});

test.each([
	['/projects/p1/runs/r1', 'PR run', 'Projects'],
	['/runs/r1', 'PR run', 'PR runs'],
	['/projects/p1', 'Project', 'Projects'],
	['/settings/ai-catalogs', 'AI catalogs', 'AI catalogs'],
	['/nowhere', 'Page not found', null]
])('%s is labeled %s in the top bar', (path, label, activeName) => {
	page.url = new URL(`http://hub.test${path}`);
	render(AppShell, { children });
	expect(screen.getAllByText(label, { selector: 'header span' })).toHaveLength(2);
	const active = nav().querySelector('[aria-current="page"]');
	expect(active?.textContent?.trim() ?? null).toBe(activeName);
});
