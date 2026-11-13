import { afterEach, expect, test } from 'vitest';
import {
	ADMIN_GROUP,
	NAV_GROUPS,
	activeHref,
	pageLabel,
	readGroupOpen,
	writeGroupOpen
} from './app-shell-nav';

afterEach(() => localStorage.clear());

test('every routed screen has exactly one navigation link', () => {
	const hrefs = [...NAV_GROUPS, ADMIN_GROUP].flatMap((group) => group.items.map((i) => i.href));
	expect(new Set(hrefs).size).toBe(hrefs.length);
	const routes = Object.keys(import.meta.glob('/src/routes/**/+page.svelte'))
		.map((file) => file.replace('/src/routes', '').replace('/+page.svelte', '') || '/')
		.filter((route) => !route.includes('['));
	expect([...routes].sort()).toEqual([...hrefs].sort());
});

test('only System is collapsible', () => {
	expect(NAV_GROUPS.filter((group) => group.collapsible).map((group) => group.id)).toEqual([
		'system'
	]);
});

test.each([
	['/', '/', 'Dashboard'],
	['/projects/runs', '/projects/runs', 'PR runs'],
	['/projects/runs/', '/projects/runs', 'PR runs'],
	['/projects/abc', '/projects', 'Project'],
	['/projects/abc/runs/def', '/projects', 'PR run'],
	['/runs/def', '/projects/runs', 'PR run'],
	['/admin/machines', '/admin/machines', 'Machine keys'],
	['/projects/abc/other', null, 'Page not found'],
	['/missing', null, 'Page not found']
])('%s maps to %s (%s)', (path, href, label) => {
	expect(activeHref(path)).toBe(href);
	expect(pageLabel(path)).toBe(label);
});

test('group open state round-trips through storage and defaults closed', () => {
	expect(readGroupOpen('system')).toBe(false);
	writeGroupOpen('system', true);
	expect(readGroupOpen('system')).toBe(true);
	writeGroupOpen('system', false);
	expect(readGroupOpen('system')).toBe(false);
});
