import { api } from '$lib/api';
import { apiErrorMessage } from '$lib/api/errors';
import type { RepoBlob, RepoInfo, RepoTree } from './types';
import type { RepositoryDataSource as ViewerDataSource } from 'devkit-viewer';

export interface RepositoryDataSource extends ViewerDataSource {
	refs(signal: AbortSignal): Promise<{ default_branch: string; branches: string[] }>;
	info(signal: AbortSignal): Promise<RepoInfo>;
	tree(path: string, ref: string, signal: AbortSignal): Promise<RepoTree>;
	blob(path: string, ref: string, signal: AbortSignal): Promise<RepoBlob>;
}

/** Viewer reads share the client's authentication, renewal and session fencing. */
export function repositoryDataSource(projectId: string, client = api): RepositoryDataSource {
	return {
		async info(signal) {
			const result = await client.GET('/api/v1/projects/{project_id}/repository/info', {
				params: { path: { project_id: projectId } },
				signal
			});
			if (!result.data)
				throw new Error(apiErrorMessage(result.error, 'Could not load repository info'));
			return result.data;
		},
		async refs(signal) {
			const info = await this.info(signal);
			if (info.branches_complete === false) throw new Error('Branch listing is incomplete');
			return { default_branch: info.default_branch, branches: info.branches ?? [] };
		},
		async tree(path, ref, signal) {
			const result = await client.GET('/api/v1/projects/{project_id}/repository/tree', {
				params: { path: { project_id: projectId }, query: { path, ref } },
				signal
			});
			if (!result.data)
				throw new Error(apiErrorMessage(result.error, 'Could not load directory tree'));
			return result.data;
		},
		async blob(path, ref, signal) {
			const result = await client.GET('/api/v1/projects/{project_id}/repository/blob', {
				params: { path: { project_id: projectId }, query: { path, ref } },
				signal
			});
			if (!result.data)
				throw new Error(apiErrorMessage(result.error, 'Could not load file content'));
			return result.data;
		}
	};
}
