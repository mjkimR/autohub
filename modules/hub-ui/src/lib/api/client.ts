import createClient, { type Client } from 'openapi-fetch';
import { apiBaseUrl, BROWSER_HEADERS, LOGOUT_PATH, REFRESH_PATH } from '$lib/config';
import { session, type TokenPair } from '$lib/stores/session.svelte';
import type { paths } from './schema';

function baseUrl(): string {
	return (
		apiBaseUrl() ||
		(typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8389')
	);
}

let refreshing: { generation: number; promise: Promise<boolean> } | null = null;

/** Concurrent renewals share one exchange only while they belong to the same signed-in session. */
export function refreshSession(fetcher: typeof fetch = fetch): Promise<boolean> {
	const generation = session.generation;
	if (refreshing?.generation === generation) return refreshing.promise;
	const promise = (async () => {
		try {
			const response = await fetcher(`${baseUrl()}${REFRESH_PATH}`, {
				method: 'POST',
				headers: BROWSER_HEADERS,
				credentials: 'include'
			});
			if (!response.ok) return false;
			return session.refreshTokens((await response.json()) as TokenPair, generation);
		} catch {
			return false;
		}
	})();
	const exchange = { generation, promise };
	refreshing = exchange;
	void promise.finally(() => {
		if (refreshing === exchange) refreshing = null;
	});
	return promise;
}

export function createApiClient(): Client<paths> {
	const client = createClient<paths>({ baseUrl: baseUrl(), credentials: 'include' });
	// A request body can be read once, so a copy is kept until the response shows whether a retry is needed.
	const retryable = new Map<string, { request: Request; generation: number }>();

	client.use({
		onRequest({ request, id }) {
			const path = new URL(request.url).pathname;
			if (path.startsWith('/api/v1/auth/')) {
				request.headers.set('X-Browser-Session', '1');
			} else if (session.accessToken) {
				request.headers.set('Authorization', `Bearer ${session.accessToken}`);
			}
			retryable.set(id, { request: request.clone(), generation: session.generation });
			return request;
		},
		onError({ id }) {
			// Failed and aborted fetches never reach onResponse.
			retryable.delete(id);
		},
		async onResponse({ request, response, id }) {
			const copy = retryable.get(id);
			retryable.delete(id);
			const path = new URL(request.url).pathname;
			if (
				response.status !== 401 ||
				path.startsWith('/api/v1/auth/') ||
				path === '/api/v1/users/login/'
			) {
				return response;
			}
			if (!copy || copy.generation !== session.generation) return response;
			// Another response may already have renewed the token while this request was in flight.
			const alreadyRenewed =
				copy.request.headers.get('Authorization') !== `Bearer ${session.accessToken}` &&
				!!session.accessToken;
			if (alreadyRenewed || (await refreshSession())) {
				if (copy.generation !== session.generation) return response;
				const token = session.accessToken;
				copy.request.headers.set('Authorization', `Bearer ${token}`);
				const retried = await fetch(copy.request);
				if (retried.status !== 401) return retried;
				if (copy.generation !== session.generation || token !== session.accessToken)
					return response;
			}
			if (copy.generation === session.generation) session.logout();
			return response;
		}
	});

	return client;
}

export const api = createApiClient();

/** Revoke the server session before reporting a successful sign-out. */
export async function logoutSession(fetcher: typeof fetch = fetch): Promise<void> {
	session.generation += 1;
	// Wait for this tab's pending Set-Cookie response before deleting the cookie.
	if (refreshing) await refreshing.promise;
	const response = await fetcher(`${baseUrl()}${LOGOUT_PATH}`, {
		method: 'POST',
		headers: BROWSER_HEADERS,
		credentials: 'include'
	});
	if (!response.ok) throw new Error('Sign-out failed. Please try again.');
	session.logout(true);
}
