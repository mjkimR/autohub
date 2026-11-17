import { api } from '$lib/api';
import { apiErrorMessage } from '$lib/api/errors';
import type { RepoBlob, RepoInfo, RepoPaths, RepoTree } from './types';

export interface RepositoryDataSource {
	refs(signal: AbortSignal): Promise<{ default_branch: string; branches: string[] }>;
	info(signal: AbortSignal): Promise<RepoInfo>;
	tree(path: string, ref: string, signal: AbortSignal): Promise<RepoTree>;
	/** `sha` is the file's blob SHA from a listing of the same ref; Hub may then answer from its cache. */
	blob(path: string, ref: string, signal: AbortSignal, sha?: string): Promise<RepoBlob>;
	/** Every path of the ref's tree in one read; `truncated` means list directories one by one. */
	paths?(ref: string, signal: AbortSignal): Promise<RepoPaths>;
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
		async paths(ref, signal) {
			const result = await client.GET('/api/v1/projects/{project_id}/repository/paths', {
				params: { path: { project_id: projectId }, query: { ref } },
				signal
			});
			if (!result.data)
				throw new Error(apiErrorMessage(result.error, 'Could not load repository paths'));
			return result.data;
		},
		async blob(path, ref, signal, sha) {
			const result = await client.GET('/api/v1/projects/{project_id}/repository/blob', {
				params: {
					path: { project_id: projectId },
					query: sha ? { path, ref, sha } : { path, ref }
				},
				signal
			});
			if (!result.data)
				throw new Error(apiErrorMessage(result.error, 'Could not load file content'));
			return result.data;
		}
	};
}
