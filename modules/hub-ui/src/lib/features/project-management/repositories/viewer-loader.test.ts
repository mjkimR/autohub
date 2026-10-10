import { afterEach, expect, test, vi } from 'vitest';
import { loadViewer, readViewerRegistry } from './viewer-loader';
import type { InstalledViewer } from './types';

afterEach(() => vi.unstubAllGlobals());
const viewer = (id: string): InstalledViewer => ({
	id,
	label: `${id} renderer`,
	tagName: `${id}-repo-viewer`,
	scriptUrl: `/plugins/repository-viewers/${id}/viewer.${'0'.repeat(64)}.js`,
	version: '0'.repeat(64)
});

for (const id of ['specs', 'architecture']) {
	if (!customElements.get(`${id}-repo-viewer`))
		customElements.define(`${id}-repo-viewer`, class extends HTMLElement {});
}

test('different repositories select different installed renderers by ID', async () => {
	vi.stubGlobal(
		'fetch',
		vi.fn(
			async () =>
				new Response(JSON.stringify({ viewers: [viewer('specs'), viewer('architecture')] }))
		)
	);
	const [first, second] = await Promise.all([
		loadViewer({ viewerId: 'specs' }),
		loadViewer({ viewerId: 'architecture' })
	]);
	expect(first.tagName).toBe('specs-repo-viewer');
	expect(second.tagName).toBe('architecture-repo-viewer');
});

test('a missing installation reports an error and can be retried after installation', async () => {
	const fetcher = vi.fn(async () => new Response('', { status: 404 }));
	vi.stubGlobal('fetch', fetcher);
	await expect(loadViewer({ viewerId: 'missing' })).rejects.toThrow('not installed');
	await expect(loadViewer({ viewerId: 'missing' })).rejects.toThrow('not installed');
	expect(fetcher).toHaveBeenCalledTimes(2);
});

test('registry rejects unexpected bundle URLs before importing code', async () => {
	vi.stubGlobal(
		'fetch',
		vi.fn(
			async () =>
				new Response(
					JSON.stringify({
						viewers: [{ ...viewer('other'), scriptUrl: 'https://other.example/viewer.js' }]
					})
				)
		)
	);
	await expect(readViewerRegistry()).rejects.toThrow('Invalid repository viewer registry entry');
});

test('registry rejects duplicate custom element tags', async () => {
	vi.stubGlobal(
		'fetch',
		vi.fn(
			async () =>
				new Response(
					JSON.stringify({
						viewers: [viewer('one'), { ...viewer('two'), tagName: 'one-repo-viewer' }]
					})
				)
		)
	);
	await expect(readViewerRegistry()).rejects.toThrow('Invalid repository viewer registry entry');
});
