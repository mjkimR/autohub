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
