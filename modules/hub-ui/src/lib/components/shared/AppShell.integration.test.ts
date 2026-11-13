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

let counts: () => Promise<unknown>;
let admin = false;

beforeEach(() => {
	admin = false;
	localStorage.clear();
	page.url = new URL('http://hub.test/decisions');
	counts = async () => ({ data: countsOf(0) });
	api.GET.mockReset();
	api.GET.mockImplementation(async (path: string) => {
		if (path === '/api/health') return { data: { status: 'ok' } };
		if (path === '/api/v1/users/me') return { data: { is_superadmin: admin } };
		if (path === '/api/v1/owed-items/counts') return counts();
		throw new Error(`unexpected ${path}`);
	});
});
afterEach(() => cleanup());

const children = createRawSnippet(() => ({ render: () => '<p>content</p>' }));
const nav = () => screen.getByRole('navigation', { name: 'Primary navigation' });
const rules = () => document.querySelectorAll('[data-owed-rule]');
const countsOf = (total: number, decision = 0) => ({
	total,
	by_kind: { decision, 'stopped-run': total - decision, 'failed-run': 4 },
	by_project: total ? { p1: total } : {}
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

test('owed items light the top rule and badge the Attention link', async () => {
	counts = async () => ({ data: countsOf(3, 2) });
	render(AppShell, { children });
	const link = await within(nav()).findByRole('link', { name: 'Attention 3 items need you' });
	expect(link.getAttribute('href')).toBe('/');
	expect(link.querySelector('[data-owed-count]')?.className).toContain('attention');
	expect(rules()).toHaveLength(2);
	const narrow = screen.getByRole('link', { name: 'Attention: 3 items need you' });
	expect(narrow.getAttribute('href')).toBe('/');
	expect(narrow.textContent).toContain('Needs you · 3');
	// One counts read serves the shell; the decision inbox is not read for the badge.
	expect(api.GET).toHaveBeenCalledWith('/api/v1/owed-items/counts');
	expect(api.GET).not.toHaveBeenCalledWith('/api/v1/pipeline-runs/decisions', expect.anything());
	expect(api.GET.mock.calls.filter(([path]) => path === '/api/v1/owed-items/counts')).toHaveLength(
		1
	);
});

test('Decisions shows the decision part of the same response, without attention', async () => {
	counts = async () => ({ data: countsOf(3, 2) });
	render(AppShell, { children });
	const link = await within(nav()).findByRole('link', { name: 'Decisions 2 pending decisions' });
	const badge = link.querySelector('[data-decision-count]')!;
	expect(badge.textContent).toContain('2');
	expect(badge.className).not.toContain('attention');
});

test('failed runs alone are not counted: total zero stays neutral', async () => {
	counts = async () => ({
		data: { total: 0, by_kind: { decision: 0, 'failed-run': 5 }, by_project: {} }
	});
	render(AppShell, { children });
	await waitFor(() => expect(api.GET).toHaveBeenCalledWith('/api/v1/owed-items/counts'));
	await new Promise((resolve) => setTimeout(resolve, 0));
	expect(within(nav()).getByRole('link', { name: 'Attention' })).toBeTruthy();
	expect(within(nav()).getByRole('link', { name: 'Decisions' })).toBeTruthy();
	expect(rules()).toHaveLength(0);
	expect(document.querySelector('[data-owed-count]')).toBeNull();
	expect(document.querySelector('[data-owed-unknown]')).toBeNull();
	expect(document.querySelector('[data-decision-count]')).toBeNull();
	expect(screen.queryByRole('link', { name: /Attention: / })).toBeNull();
});

test('a backlog is shown exactly', async () => {
	counts = async () => ({ data: countsOf(137, 100) });
	render(AppShell, { children });
	await within(nav()).findByRole('link', { name: 'Attention 137 items need you' });
	expect(screen.getByText('Needs you · 137')).toBeTruthy();
	expect(screen.queryByText(/\+/)).toBeNull();
});

test('one owed item uses the singular', async () => {
	counts = async () => ({ data: countsOf(1, 1) });
	render(AppShell, { children });
	await within(nav()).findByRole('link', { name: 'Attention 1 item needs you' });
	await within(nav()).findByRole('link', { name: 'Decisions 1 pending decision' });
});

test.each([
	['error', async () => ({ error: { detail: 'down' } })],
	['failure', async () => Promise.reject(new Error('offline'))],
	['invalid count', async () => ({ data: { by_kind: {}, by_project: {} } })],
	['negative count', async () => ({ data: { total: -1, by_kind: {}, by_project: {} } })],
	['loading', () => new Promise(() => {})]
])('%s shows a neutral unknown mark, not zero or debt', async (_name, response) => {
	counts = response;
	render(AppShell, { children });
	await waitFor(() => expect(api.GET).toHaveBeenCalledWith('/api/v1/owed-items/counts'));
	await new Promise((resolve) => setTimeout(resolve, 0));
	const link = within(nav()).getByRole('link', { name: 'Attention Owed items unknown' });
	const mark = link.querySelector('[data-owed-unknown]')!;
	expect(mark.textContent).toContain('?');
	expect(mark.getAttribute('title')).toBe('Owed items unknown');
	expect(mark.className).not.toContain('attention');
	const narrow = screen.getByRole('link', { name: 'Attention: Owed items unknown' });
	expect(narrow.getAttribute('href')).toBe('/');
	expect(narrow.getAttribute('title')).toBe('Owed items unknown');
	expect(narrow.innerHTML).not.toContain('attention');
	expect(rules()).toHaveLength(0);
	expect(document.querySelector('[data-owed-count]')).toBeNull();
	expect(document.querySelector('[data-decision-count]')).toBeNull();
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
	expect(names('attention')).toEqual(['Attention', 'Decisions']);
	expect(names('work')).toEqual(['Projects', 'PR runs']);
	expect(names('setup')).toEqual(['Connectors', 'AI catalogs', 'Notifications']);
	expect(names('system')).toEqual([
		'Health',
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
	['/', 'Attention', 'Attention'],
	['/system/health', 'Health', 'Health'],
	['/nowhere', 'Page not found', null]
])('%s is labeled %s in the top bar', (path, label, activeName) => {
	page.url = new URL(`http://hub.test${path}`);
	render(AppShell, { children });
	expect(screen.getAllByText(label, { selector: 'header span' })).toHaveLength(2);
	const active = nav().querySelector('[aria-current="page"]');
	expect(active?.querySelector('span')?.textContent?.trim() ?? null).toBe(activeName);
});
