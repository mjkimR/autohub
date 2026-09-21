import createClient, { type Client } from 'openapi-fetch';
import { apiBaseUrl, LOGIN_PATH, REFRESH_PATH } from '$lib/config';
import { session, type TokenPair } from '$lib/stores/session.svelte';
import type { paths } from './schema';

export class ApiError extends Error {
	constructor(
		readonly status: number,
		readonly path: string,
		message?: string
	) {
		super(message ?? `${path} failed with status ${status}`);
		this.name = 'ApiError';
	}
}

function baseUrl(): string {
	return (
		apiBaseUrl() ||
		(typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8389')
	);
}

let refreshing: Promise<boolean> | null = null;

/** Exchange the refresh token for a new pair. Concurrent callers share one exchange. */
export function refreshSession(fetcher: typeof fetch = fetch): Promise<boolean> {
	if (!session.refreshToken) return Promise.resolve(false);
	refreshing ??= (async () => {
		try {
			const response = await fetcher(`${baseUrl()}${REFRESH_PATH}`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ refresh_token: session.refreshToken })
			});
			if (!response.ok) return false;
			session.setTokens((await response.json()) as TokenPair);
			return true;
		} catch {
			return false;
		} finally {
			refreshing = null;
		}
	})();
	return refreshing;
}

export function createApiClient(): Client<paths> {
	const client = createClient<paths>({ baseUrl: baseUrl() });
	// A request body can be read once, so a copy is kept until the response shows whether a retry is needed.
	const retryable = new Map<string, Request>();

	client.use({
		onRequest({ request, id }) {
			if (session.accessToken) {
				request.headers.set('Authorization', `Bearer ${session.accessToken}`);
			}
			retryable.set(id, request.clone());
			return request;
		},
		async onResponse({ request, response, id }) {
			const copy = retryable.get(id);
			retryable.delete(id);
			const path = new URL(request.url).pathname;
			if (response.status !== 401 || path === LOGIN_PATH || path === REFRESH_PATH) {
				return response;
			}
			// The access token expired (or was never valid): renew the session once and repeat the request.
			if (copy && (await refreshSession())) {
				copy.headers.set('Authorization', `Bearer ${session.accessToken}`);
				const retried = await fetch(copy);
				if (retried.status !== 401) return retried;
			}
			session.logout();
			return response;
		}
	});

	return client;
}

export const api = createApiClient();
