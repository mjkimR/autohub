export const projectTabs = [
	{ id: 'overview', label: 'Overview' },
	{ id: 'runs', label: 'Runs' },
	{ id: 'plans', label: 'Plans' },
	{ id: 'connections', label: 'Connections' },
	{ id: 'automation', label: 'Automation' },
	{ id: 'settings', label: 'Settings' }
] as const;
export type ProjectTab = (typeof projectTabs)[number]['id'];
export function projectTab(value: string | null): ProjectTab {
	return projectTabs.find((tab) => tab.id === value)?.id ?? 'overview';
}
