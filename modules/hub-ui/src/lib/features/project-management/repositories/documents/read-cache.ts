import type { RepositoryDataSource } from '../data-source';
import type { RepoBlob, RepoItem, RepoTree } from '../types';

type Snapshot = { dirs: Map<string, RepoItem[]>; shas: Map<string, string> } | null;

/** Directory children from a whole-tree listing, sorted like Hub's directory listing. */
function snapshotOf(items: RepoItem[]): NonNullable<Snapshot> {
	const dirs = new Map<string, RepoItem[]>([['', []]]);
	const shas = new Map<string, string>();
	for (const item of items) {
		if (item.type === 'dir' && !dirs.has(item.path)) dirs.set(item.path, []);
		if (item.type === 'file' && item.sha) shas.set(item.path, item.sha);
	}
	for (const item of items) {
		const parent = item.path.includes('/') ? item.path.slice(0, item.path.lastIndexOf('/')) : '';
		dirs.get(parent)?.push(item);
	}
	for (const children of dirs.values())
		children.sort(
			(a, b) =>
				(a.type === 'dir' ? 0 : 1) - (b.type === 'dir' ? 0 : 1) ||
				a.name.toLowerCase().localeCompare(b.name.toLowerCase())
		);
	return { dirs, shas };
}

/**
 * Successful reads live only for this viewer session; aborted/failed reads never enter it. When
 * the source offers whole-tree listings, one read per ref answers every directory listing and
 * supplies blob SHAs for Hub's content cache; a failed or truncated listing falls back to
 * directory-by-directory reads.
 */
export function cacheRepositoryReads(source: RepositoryDataSource): RepositoryDataSource {
	const trees = new Map<string, RepoTree>();
	const blobs = new Map<string, RepoBlob>();
	const snapshots = new Map<string, Promise<Snapshot>>();
	async function read<T>(
		cache: Map<string, T>,
		key: string,
		signal: AbortSignal,
		fetch: () => Promise<T>
	) {
		signal.throwIfAborted();
		if (cache.has(key)) return cache.get(key)!;
		const value = await fetch();
		signal.throwIfAborted();
		// Bound retained content even in a large repository. Eviction only causes a fresh read.
		if (cache.size >= 300) cache.delete(cache.keys().next().value!);
		cache.set(key, value);
		return value;
	}
	function snapshot(ref: string): Promise<Snapshot> {
		if (!source.paths) return Promise.resolve(null);
		let pending = snapshots.get(ref);
		if (!pending) {
			// Shared by every caller of this ref, so one caller's cancellation never cancels it.
			pending = source
				.paths(ref, new AbortController().signal)
				.then((listing) => (listing.truncated ? null : snapshotOf(listing.items ?? [])))
				.catch(() => null);
			snapshots.set(ref, pending);
		}
		return pending;
	}
	return {
		info: (signal) => source.info(signal),
		refs: (signal) => source.refs(signal),
		paths: source.paths && ((ref, signal) => source.paths!(ref, signal)),
		tree: (path, ref, signal) =>
			read(trees, JSON.stringify([ref, path]), signal, async () => {
				const known = (await snapshot(ref))?.dirs.get(path);
				signal.throwIfAborted();
				return known ? { path, ref, items: known } : source.tree(path, ref, signal);
			}),
		blob: (path, ref, signal) =>
			read(blobs, JSON.stringify([ref, path]), signal, async () => {
				const sha = snapshots.has(ref) ? (await snapshot(ref))?.shas.get(path) : undefined;
				return sha ? source.blob(path, ref, signal, sha) : source.blob(path, ref, signal);
			})
	};
}
