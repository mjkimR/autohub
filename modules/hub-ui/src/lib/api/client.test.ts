import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { session } from '$lib/stores/session.svelte';
import { createApiClient } from './client';

const json = (status: number, body: unknown) =>
	new Response(JSON.stringify(body), {
		status,
		headers: { 'Content-Type': 'application/json' }
	});

let calls: { url: string; authorization: string | null; body: string }[];
let respond: (url: string, authorization: string | null) => Response;

beforeEach(() => {
	calls = [];
	session.setTokens({ access_token: 'expired', refresh_token: 'refresh-1' });
	vi.stubGlobal(
		'fetch',
		vi.fn(async (input: Request | string, init?: RequestInit) => {
			const request = input instanceof Request ? input : new Request(input, init);
			const authorization = request.headers.get('Authorization');
			calls.push({ url: new URL(request.url).pathname, authorization, body: await request.text() });
			return respond(new URL(request.url).pathname, authorization);
		})
	);
});

afterEach(() => {
	vi.unstubAllGlobals();
	session.logout();
});

test('an expired access token is renewed once and the request repeated with its body', async () => {
	respond = (url, authorization) => {
		if (url === '/api/v1/users/login/refresh')
			return json(200, { access_token: 'fresh', refresh_token: 'refresh-2', token_type: 'bearer' });
		return authorization === 'Bearer fresh' ? json(201, { id: 'c1' }) : json(401, {});
	};

	const res = await createApiClient().POST('/api/v1/connectors', {
		body: {
			name: 'PAT',
			provider: 'github',
			config: {},
			enabled: true,
			credentials: { token: 't' }
		}
	});

	expect(res.response.status).toBe(201);
	expect(calls.map((call) => [call.url, call.authorization])).toEqual([
		['/api/v1/connectors', 'Bearer expired'],
		['/api/v1/users/login/refresh', null],
		['/api/v1/connectors', 'Bearer fresh']
	]);
	expect(calls[2].body).toBe(calls[0].body);
	expect(JSON.parse(calls[1].body)).toEqual({ refresh_token: 'refresh-1' });
	// The session now holds the new pair.
	expect([session.accessToken, session.refreshToken]).toEqual(['fresh', 'refresh-2']);
});

test('a session that cannot be renewed is signed out', async () => {
	respond = () => json(401, {});

	const res = await createApiClient().GET('/api/v1/connectors', {});

	expect(res.response.status).toBe(401);
	expect(session.isAuthenticated).toBe(false);
	expect(session.refreshToken).toBe('');
});

test('requests made together share one renewal', async () => {
	respond = (url, authorization) => {
		if (url === '/api/v1/users/login/refresh')
			return json(200, { access_token: 'fresh', refresh_token: 'refresh-2', token_type: 'bearer' });
		return authorization === 'Bearer fresh' ? json(200, { items: [] }) : json(401, {});
	};
	const client = createApiClient();

	await Promise.all([
		client.GET('/api/v1/connectors', {}),
		client.GET('/api/v1/projects', {}),
		client.GET('/api/v1/ai-catalogs')
	]);

	expect(calls.filter((call) => call.url === '/api/v1/users/login/refresh')).toHaveLength(1);
});

test('a failed sign-in is not mistaken for an expired session', async () => {
	respond = () => json(401, {});

	await createApiClient().POST('/api/v1/users/login/', {
		body: { username: 'a@example.com', password: 'x', scope: '' },
		bodySerializer: (body) => new URLSearchParams(body as Record<string, string>)
	});

	expect(calls.map((call) => call.url)).toEqual(['/api/v1/users/login/']);
});
