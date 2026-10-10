import { api } from '$lib/api';
import { apiErrorMessage } from '$lib/api/errors';
import type { RepoBlob, RepoInfo, RepoTree } from './types';

export interface RepositoryDataSource {
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
