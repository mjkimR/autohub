import {
	Bot,
	BellRing,
	CalendarClock,
	FileCode,
	FolderKanban,
	History,
	Inbox,
	KeyRound,
	KeySquare,
	LayoutDashboard,
	Settings,
	UserCheck,
	Webhook,
	Workflow
} from '@lucide/svelte';
import type { Component } from 'svelte';

export type NavItem = {
	href: string;
	label: string;
	icon: Component<{ class?: string }>;
};

export type NavGroup = {
	id: string;
	label: string;
	items: readonly NavItem[];
	/** Diagnostic groups start collapsed and open themselves when they hold the current page. */
	collapsible?: boolean;
};

export const DECISIONS_HREF = '/decisions';

// Grouped by operator job: what is owed, the work itself, setup, then diagnostics.
export const NAV_GROUPS: readonly NavGroup[] = [
	{
		id: 'attention',
		label: 'Attention',
		items: [
			{ href: '/', label: 'Dashboard', icon: LayoutDashboard },
			{ href: DECISIONS_HREF, label: 'Decisions', icon: Inbox }
		]
	},
	{
		id: 'work',
		label: 'Work',
		items: [
			{ href: '/projects', label: 'Projects', icon: FolderKanban },
			{ href: '/projects/runs', label: 'PR runs', icon: Workflow }
		]
	},
	{
		id: 'setup',
		label: 'Setup',
		items: [
			{ href: '/settings/connectors', label: 'Connectors', icon: KeyRound },
			{ href: '/settings/ai-catalogs', label: 'AI catalogs', icon: Bot },
			{ href: '/settings/notifications', label: 'Notifications', icon: BellRing }
		]
	},
	{
		id: 'system',
		label: 'System',
		collapsible: true,
		items: [
			{ href: '/schedules/configs', label: 'Schedule configs', icon: CalendarClock },
			{ href: '/schedules/jobs', label: 'Schedule jobs', icon: History },
			{ href: '/operations/webhooks', label: 'Webhook deliveries', icon: Webhook },
			{ href: '/operations/tasks', label: 'Task specs', icon: FileCode },
			{ href: '/settings/system', label: 'System configs', icon: Settings }
		]
	}
];

export const ADMIN_GROUP: NavGroup = {
	id: 'admin',
	label: 'Administration',
	items: [
		{ href: '/admin/users', label: 'Account approval', icon: UserCheck },
		{ href: '/admin/machines', label: 'Machine keys', icon: KeySquare }
	]
};

const ALL_GROUPS = [...NAV_GROUPS, ADMIN_GROUP];

/** Routes without their own link highlight the list that owns them. */
const ROUTE_OWNERS: readonly { pattern: RegExp; href: string; label: string }[] = [
	{ pattern: /^\/projects\/[^/]+\/runs\/[^/]+\/?$/, href: '/projects', label: 'PR run' },
	{ pattern: /^\/runs\/[^/]+\/?$/, href: '/projects/runs', label: 'PR run' },
	{ pattern: /^\/projects\/[^/]+\/?$/, href: '/projects', label: 'Project' }
];

function normalize(pathname: string) {
	return pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname;
}

/** The nav href that represents `pathname`, or null outside the navigation. */
export function activeHref(pathname: string): string | null {
	const path = normalize(pathname);
	for (const group of ALL_GROUPS) {
		for (const item of group.items) if (item.href === path) return item.href;
	}
	return ROUTE_OWNERS.find((owner) => owner.pattern.test(path))?.href ?? null;
}

/** The top-bar label for `pathname`; unknown routes are the 404 page. */
export function pageLabel(pathname: string): string {
	const path = normalize(pathname);
	for (const group of ALL_GROUPS) {
		for (const item of group.items) if (item.href === path) return item.label;
	}
	return ROUTE_OWNERS.find((owner) => owner.pattern.test(path))?.label ?? 'Page not found';
}

export function groupHolds(group: NavGroup, href: string | null) {
	return href !== null && group.items.some((item) => item.href === href);
}

const storageKey = (groupId: string) => `autohub.nav.${groupId}.open`;

/** Remembered open state for a collapsible group; storage may be unavailable, so default closed. */
export function readGroupOpen(groupId: string): boolean {
	try {
		return globalThis.localStorage?.getItem(storageKey(groupId)) === 'true';
	} catch {
		return false;
	}
}

export function writeGroupOpen(groupId: string, open: boolean) {
	try {
		globalThis.localStorage?.setItem(storageKey(groupId), String(open));
	} catch {
		// Private windows and blocked storage keep the in-memory choice only.
	}
}
