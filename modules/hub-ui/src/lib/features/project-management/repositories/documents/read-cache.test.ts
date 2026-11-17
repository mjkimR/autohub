import { expect, test, vi } from 'vitest';
import { cacheRepositoryReads } from './read-cache';
import { sourceFor } from './fixtures';

test('reuses successful same-ref reads, separates branches and honors cancellation', async () => {
	const source = sourceFor({ 'docs/a.md': '# A' });
	const cached = cacheRepositoryReads(source),
		signal = new AbortController().signal;
	await cached.blob('docs/a.md', 'main', signal);
	await cached.blob('docs/a.md', 'main', signal);
	await cached.tree('docs', 'main', signal);
	await cached.tree('docs', 'main', signal);
	expect(source.blob).toHaveBeenCalledTimes(1);
	expect(source.tree).toHaveBeenCalledTimes(1);
	await cached.blob('docs/a.md', 'other', signal);
	expect(source.blob).toHaveBeenCalledTimes(2);
	const aborted = new AbortController();
	aborted.abort();
	await expect(cached.blob('docs/a.md', 'main', aborted.signal)).rejects.toThrow();
});

test('failed or canceled reads are not retained and a fresh session invalidates old content', async () => {
	const source = sourceFor({ 'docs/a.md': '# A' });
	const original = source.blob;
	source.blob = vi.fn().mockRejectedValueOnce(new Error('Temporary')).mockImplementation(original);
	const cached = cacheRepositoryReads(source),
		signal = new AbortController().signal;
	await expect(cached.blob('docs/a.md', 'main', signal)).rejects.toThrow('Temporary');
	await cached.blob('docs/a.md', 'main', signal);
	await cacheRepositoryReads(source).blob('docs/a.md', 'main', signal);
	expect(source.blob).toHaveBeenCalledTimes(3);
});

/** The fixture's directories plus a whole-tree listing built from the same documents. */
function withPaths(documents: Record<string, string>, truncated = false) {
	const source = sourceFor(documents);
	const items = new Map<
		string,
		{ name: string; path: string; type: 'dir' | 'file'; size: number; sha: string }
	>();
	for (const path of Object.keys(documents)) {
		const parts = path.split('/');
		parts.forEach((name, i) => {
			const child = parts.slice(0, i + 1).join('/');
			const file = i === parts.length - 1;
			items.set(child, {
				name,
				path: child,
				type: file ? 'file' : 'dir',
				size: 1,
				sha: file ? `sha-${child}` : ''
			});
		});
	}
	source.paths = vi.fn(async (ref: string) => ({
		ref,
		sha: 'root',
		truncated,
		items: truncated ? [] : [...items.values()]
	}));
	return source;
}

test('one whole-tree listing answers every directory and passes blob SHAs on', async () => {
	const documents = {
		'docs/b.md': '# B',
		'docs/A.md': '# A',
		'docs/sub/c.md': '# C',
		'README.md': '#'
	};
	const source = withPaths(documents);
	const cached = cacheRepositoryReads(source),
		signal = new AbortController().signal;
	const root = await cached.tree('', 'main', signal);
	const docs = await cached.tree('docs', 'main', signal);
	expect((root.items ?? []).map((i) => i.path)).toEqual(['docs', 'README.md']);
	expect((docs.items ?? []).map((i) => i.name)).toEqual(['sub', 'A.md', 'b.md']);
	expect(source.paths).toHaveBeenCalledTimes(1);
	expect(source.tree).not.toHaveBeenCalled();
	await cached.blob('docs/A.md', 'main', signal);
	expect(source.blob).toHaveBeenCalledWith('docs/A.md', 'main', signal, 'sha-docs/A.md');
	// A path outside the listing still asks Hub, which reports the real result.
	await cached.tree('missing', 'main', signal);
	expect(source.tree).toHaveBeenCalledTimes(1);
});

test('a truncated or failed whole-tree listing falls back to directory reads', async () => {
	const signal = new AbortController().signal;
	const truncated = withPaths({ 'docs/a.md': '# A' }, true);
	await cacheRepositoryReads(truncated).tree('docs', 'main', signal);
	expect(truncated.tree).toHaveBeenCalledTimes(1);
	const failing = withPaths({ 'docs/a.md': '# A' });
	failing.paths = vi.fn().mockRejectedValue(new Error('Forbidden'));
	const cached = cacheRepositoryReads(failing);
	expect(((await cached.tree('docs', 'main', signal)).items ?? []).map((i) => i.path)).toEqual([
		'docs/a.md'
	]);
	await cached.blob('docs/a.md', 'main', signal);
	expect(failing.blob).toHaveBeenCalledWith('docs/a.md', 'main', signal);
});

test('a document read alone does not request a whole-tree listing', async () => {
	const source = withPaths({ 'docs/a.md': '# A' });
	const signal = new AbortController().signal;
	await cacheRepositoryReads(source).blob('docs/a.md', 'main', signal);
	expect(source.paths).not.toHaveBeenCalled();
	expect(source.blob).toHaveBeenCalledWith('docs/a.md', 'main', signal);
});
