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

test.each([new TypeError('offline'), new DOMException('Canceled', 'AbortError')])(
	'a failed fetch propagates its error and the client can renew on the next request: %s',
	async (error) => {
		const client = createApiClient();
		respond = () => {
			throw error;
		};
		await expect(client.GET('/api/v1/connectors', {})).rejects.toBe(error);
		expect(session.accessToken).toBe('expired');
		expect(calls).toHaveLength(1);

		respond = (url, authorization) => {
			if (url === '/api/v1/users/login/refresh')
				return json(200, { access_token: 'fresh', refresh_token: 'refresh-2' });
			return authorization === 'Bearer fresh' ? json(200, { items: [] }) : json(401, {});
		};
		expect((await client.GET('/api/v1/connectors', {})).response.status).toBe(200);
		expect(session.accessToken).toBe('fresh');
	}
);

test('a late renewal cannot sign the user back in after logout', async () => {
	const { refreshSession } = await import('./client');
	let finish!: (response: Response) => void;
	const renewing = refreshSession(
		() =>
			new Promise((resolve) => {
				finish = resolve;
			})
	);
	session.logout();
	finish(json(200, { access_token: 'stale', refresh_token: 'stale-refresh' }));
	expect(await renewing).toBe(false);
	expect(session.isAuthenticated).toBe(false);
});

test.each([200, 401])(
	'an old session response (%s) cannot overwrite or log out a newer sign-in',
	async (status) => {
		let finish!: (response: Response) => void;
		let started!: () => void;
		const refreshing = new Promise<void>((resolve) => {
			started = resolve;
		});
		vi.stubGlobal(
			'fetch',
			vi.fn(async (input: Request | string) => {
				const url = typeof input === 'string' ? input : input.url;
				if (url.includes('/refresh')) {
					started();
					return new Promise<Response>((resolve) => {
						finish = resolve;
					});
				}
				return json(401, {});
			})
		);
		const request = createApiClient().GET('/api/v1/connectors', {});
		await refreshing;
		session.setTokens({ access_token: 'new-login', refresh_token: 'new-refresh' });
		finish(json(status, { access_token: 'stale', refresh_token: 'stale-refresh' }));
		await request;
		expect(session.accessToken).toBe('new-login');
		expect(session.refreshToken).toBe('new-refresh');
	}
);

test('a delayed 401 reuses the token another request already renewed', async () => {
	let finish!: (response: Response) => void;
	let started!: () => void;
	const pending = new Promise<void>((resolve) => {
		started = resolve;
	});
	let renewals = 0;
	vi.stubGlobal(
		'fetch',
		vi.fn(async (input: Request | string) => {
			const url = typeof input === 'string' ? input : input.url;
			if (url.includes('/refresh')) {
				renewals++;
				return json(200, { access_token: 'fresh', refresh_token: 'refresh-2' });
			}
			const request = input as Request;
			if (request.headers.get('Authorization') === 'Bearer fresh') return json(200, { items: [] });
			if (url.endsWith('/projects')) {
				started();
				return new Promise<Response>((resolve) => {
					finish = resolve;
				});
			}
			return json(401, {});
		})
	);
	const client = createApiClient();
	const delayed = client.GET('/api/v1/projects', {});
	await pending;
	await client.GET('/api/v1/connectors', {});
	finish(json(401, {}));
	expect((await delayed).response.status).toBe(200);
	expect(renewals).toBe(1);
});
