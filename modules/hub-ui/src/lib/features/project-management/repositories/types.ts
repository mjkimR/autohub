import type { components } from '$lib/api';

export type RepoItem = components['schemas']['RepoItemRead'];
export type RepoTree = components['schemas']['RepoTreeRead'];
export type RepoBlob = components['schemas']['RepoBlobRead'];
export type RepoInfo = components['schemas']['RepoInfoRead'];

export type ViewerMode = 'default' | 'specrig';

export interface InstalledViewer {
	id: string;
	label: string;
	scriptUrl: string;
	tagName: string;
	version: string;
	initialPath?: string;
}

export type CustomViewerConfig = InstalledViewer | { viewerId: string };
