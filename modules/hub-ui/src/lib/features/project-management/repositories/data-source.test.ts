import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { session } from '$lib/stores/session.svelte';
import { createApiClient } from '$lib/api/client';
import { repositoryDataSource } from './data-source';

const json = (status: number, body: unknown) =>
	new Response(JSON.stringify(body), {
		status,
		headers: { 'Content-Type': 'application/json' }
	});
beforeEach(() => session.setTokens({ access_token: 'expired', refresh_token: 'refresh' }));
afterEach(() => {
	vi.unstubAllGlobals();
	session.logout();
});

test('viewer requests renew the session and preserve project, path, ref and cancellation', async () => {
	const calls: Request[] = [];
	vi.stubGlobal(
		'fetch',
		vi.fn(async (input: Request | string, init?: RequestInit) => {
			const request = input instanceof Request ? input : new Request(input, init);
			calls.push(request);
			if (request.url.endsWith('/auth/browser/refresh'))
				return json(200, { access_token: 'fresh', refresh_token: 'next' });
			if (request.headers.get('Authorization') !== 'Bearer fresh') return json(401, {});
			const url = new URL(request.url);
			if (url.pathname.endsWith('/info'))
				return json(200, { default_branch: 'main', branches: ['main'] });
			if (url.pathname.endsWith('/tree'))
				return json(200, { items: [{ name: 'a.md', path: 'docs/a.md', type: 'file' }] });
			return json(200, { path: 'docs/a.md', content: '# Hello', encoding: 'utf-8' });
		})
	);
	const source = repositoryDataSource('project-1', createApiClient());
	const controller = new AbortController();
	expect((await source.tree('docs', 'feature/a', controller.signal)).items![0].type).toBe('file');
	await source.info(controller.signal);
	await source.blob('docs/a.md', 'feature/a', controller.signal);
	expect(calls.filter((request) => request.url.endsWith('/auth/browser/refresh'))).toHaveLength(1);
	expect(calls[0].headers.get('Authorization')).toBe('Bearer expired');
	expect(calls[2].headers.get('Authorization')).toBe('Bearer fresh');
	const url = new URL(calls[2].url);
	expect(url.pathname).toBe('/api/v1/projects/project-1/repository/tree');
	expect(url.searchParams.get('path')).toBe('docs');
	expect(url.searchParams.get('ref')).toBe('feature/a');
	controller.abort();
	expect(calls[2].signal.aborted).toBe(true);
});

test('repository refusals propagate to the embedded viewer', async () => {
	vi.stubGlobal(
		'fetch',
		vi.fn(async () => json(403, { detail: 'Repository access denied' }))
	);
	await expect(
		repositoryDataSource('p1', createApiClient()).blob(
			'docs/a.md',
			'main',
			new AbortController().signal
		)
	).rejects.toThrow('Repository access denied');
});
