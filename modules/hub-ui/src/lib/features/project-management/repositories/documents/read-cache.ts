import type { RepositoryDataSource } from '../data-source';
import type { RepoBlob, RepoTree } from '../types';

/** Successful reads live only for this viewer session; aborted/failed reads never enter it. */
export function cacheRepositoryReads(source: RepositoryDataSource): RepositoryDataSource {
	const trees = new Map<string, RepoTree>();
	const blobs = new Map<string, RepoBlob>();
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
	return {
		info: (signal) => source.info(signal),
		refs: (signal) => source.refs(signal),
		tree: (path, ref, signal) =>
			read(trees, JSON.stringify([ref, path]), signal, () => source.tree(path, ref, signal)),
		blob: (path, ref, signal) =>
			read(blobs, JSON.stringify([ref, path]), signal, () => source.blob(path, ref, signal))
	};
}
