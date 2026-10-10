export interface TreeItem {
	name: string;
	path: string;
	type: string;
	size?: number;
	sha?: string;
}

export type TreeResponse = TreeItem[] | { items?: TreeItem[] } | { items?: any[] } | any;
export interface RepositoryInfo {
	default_branch: string;
	repo_id?: string;
	[key: string]: any;
}
export interface RepositoryBlob {
	path: string;
	content: string;
	encoding: string;
	[key: string]: any;
}

/** Hosts own authentication and renewal; credentials never become element attributes. */
export interface RepositoryDataSource {
	info(signal: AbortSignal): Promise<any>;
	tree(path: string, ref: string, signal: AbortSignal): Promise<any>;
	blob(path: string, ref: string, signal: AbortSignal): Promise<any>;
}

export function httpDataSource(base: string): RepositoryDataSource {
	async function get<T>(endpoint: string, signal: AbortSignal): Promise<T> {
		const response = await fetch(`${base.replace(/\/+$/, '')}/${endpoint}`, { signal });
		if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
		return response.json();
	}
	const query = (path: string, ref: string) => new URLSearchParams({ path, ref });
	return {
		info: (signal) => get('info', signal),
		tree: (path, ref, signal) => get(`tree?${query(path, ref)}`, signal),
		blob: (path, ref, signal) => get(`blob?${query(path, ref)}`, signal)
	};
}

export function normalizeTree(response: TreeResponse): TreeItem[] {
	const items = Array.isArray(response) ? response : (response?.items ?? []);
	return items
		.map((item: any) => ({
			...item,
			type: item.type === 'dir' ? 'tree' : item.type === 'file' ? 'blob' : item.type
		}))
		.sort((a: any, b: any) =>
			a.type !== b.type ? (a.type === 'tree' ? -1 : 1) : a.name.localeCompare(b.name)
		);
}
