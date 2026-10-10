import type { components } from '$lib/api';

export type RepoItem = components['schemas']['RepoItemRead'];
export type RepoTree = components['schemas']['RepoTreeRead'];
export type RepoBlob = components['schemas']['RepoBlobRead'];
export type RepoInfo = components['schemas']['RepoInfoRead'];

export type ViewerMode = 'default' | 'custom';

export interface CustomViewerConfig {
	type?: string;
	scriptUrl: string;
	tagName: string;
	version?: string;
}
