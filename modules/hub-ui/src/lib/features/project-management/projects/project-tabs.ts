/**
 * Project detail sections. Work tabs hold what the project is doing; Setup tabs hold how it is
 * configured. Tab ids are the `?tab=` values that links and notices already use, so grouping
 * never changes a URL.
 */
export const projectTabGroups = [
	{
		id: 'work',
		label: 'Work',
		tabs: [
			{ id: 'overview', label: 'Overview' },
			{ id: 'runs', label: 'Runs' },
			{ id: 'plans', label: 'Plans' },
			{ id: 'repository', label: 'Repository' }
		]
	},
	{
		id: 'setup',
		label: 'Setup',
		tabs: [
			{ id: 'connections', label: 'Connections' },
			{ id: 'automation', label: 'Automation' },
			{ id: 'settings', label: 'Settings' }
		]
	}
] as const;

type ProjectTabEntry = (typeof projectTabGroups)[number]['tabs'][number];
export type ProjectTab = ProjectTabEntry['id'];
export const projectTabs: readonly ProjectTabEntry[] = projectTabGroups.flatMap(
	(group): readonly ProjectTabEntry[] => group.tabs
);

export function projectTab(value: string | null): ProjectTab {
	return projectTabs.find((tab) => tab.id === value)?.id ?? 'overview';
}

/** URL of a project section: `/projects/<id>?tab=<tab>`, the form existing links use. */
export function projectTabHref(projectId: string, tab: ProjectTab): string {
	return `/projects/${encodeURIComponent(projectId)}?tab=${tab}`;
}
