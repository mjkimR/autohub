import { cleanup, render, screen, waitFor, within } from '@testing-library/svelte';
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
	page.url = new URL('http://hub.test/decisions');
	decisions = async () => ({ data: { items: [], has_more: false, next_cursor: null } });
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
const entry = (actionable: boolean) => ({ actionable });

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
	decisions = async () => ({
		data: { items: [entry(true), entry(false), entry(true)], has_more: false, next_cursor: null }
	});
	render(AppShell, { children });
	const link = await within(nav()).findByRole('link', { name: 'Decisions 2 pending decisions' });
	expect(within(link).getByText('2')).toBeTruthy();
	expect(rules()).toHaveLength(2);
	expect(
		screen.getByRole('link', { name: 'Decisions: 2 pending decisions' }).getAttribute('href')
	).toBe('/decisions');
	expect(api.GET).toHaveBeenCalledWith('/api/v1/pipeline-runs/decisions', {
		params: { query: { limit: 50 } }
	});
});

test('a full sample is shown as a lower bound', async () => {
	decisions = async () => ({
		data: { items: [entry(true)], has_more: true, next_cursor: 'next' }
	});
	render(AppShell, { children });
	await within(nav()).findByRole('link', { name: 'Decisions 1 or more pending decisions' });
	expect(screen.getByText('1+ pending')).toBeTruthy();
});

test.each([
	['zero', async () => ({ data: { items: [entry(false)], has_more: false, next_cursor: null } })],
	['error', async () => ({ error: { detail: 'down' } })],
	['failure', async () => Promise.reject(new Error('offline'))],
	['loading', () => new Promise(() => {})]
])('%s stays neutral', async (_name, response) => {
	decisions = response;
	render(AppShell, { children });
	await waitFor(() =>
		expect(api.GET).toHaveBeenCalledWith('/api/v1/pipeline-runs/decisions', expect.anything())
	);
	await new Promise((resolve) => setTimeout(resolve, 0));
	expect(within(nav()).getByRole('link', { name: 'Decisions' })).toBeTruthy();
	expect(rules()).toHaveLength(0);
	expect(document.querySelector('[data-pending-count]')).toBeNull();
});
