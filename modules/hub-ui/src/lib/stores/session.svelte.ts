import {
	ACCESS_TOKEN_STORAGE,
	EMAIL_STORAGE,
	LEGACY_API_KEY_STORAGE,
	REFRESH_TOKEN_STORAGE
} from '$lib/config';

export type TokenPair = { access_token: string; refresh_token?: string | null };

function read(storage: 'sessionStorage' | 'localStorage', key: string): string {
	try {
		return globalThis[storage]?.getItem(key) || '';
	} catch {
		return '';
	}
}

function write(storage: 'sessionStorage' | 'localStorage', key: string, value: string) {
	try {
		if (value) globalThis[storage]?.setItem(key, value);
		else globalThis[storage]?.removeItem(key);
	} catch {
		// storage blocked
	}
}

/**
 * The signed-in session. Only tokens are kept, and only for the tab (sessionStorage): the password exists in the
 * sign-in form and nowhere else. The access token is short-lived; the refresh token renews it and dies with the
 * password it was issued under.
 */
class Session {
	accessToken = $state(read('sessionStorage', ACCESS_TOKEN_STORAGE));
	refreshToken = $state(read('sessionStorage', REFRESH_TOKEN_STORAGE));
	email = $state(read('localStorage', EMAIL_STORAGE));
	isAuthenticated = $derived(this.accessToken.length > 0);

	constructor() {
		write('sessionStorage', LEGACY_API_KEY_STORAGE, '');
		write('localStorage', LEGACY_API_KEY_STORAGE, '');
	}

	setTokens(tokens: TokenPair) {
		this.accessToken = tokens.access_token;
		// A refresh answers with a new refresh token; keep the old one only if it did not.
		this.refreshToken = tokens.refresh_token || this.refreshToken;
		write('sessionStorage', ACCESS_TOKEN_STORAGE, this.accessToken);
		write('sessionStorage', REFRESH_TOKEN_STORAGE, this.refreshToken);
	}

	rememberEmail(email: string) {
		this.email = email;
		write('localStorage', EMAIL_STORAGE, email);
	}

	logout() {
		this.accessToken = '';
		this.refreshToken = '';
		write('sessionStorage', ACCESS_TOKEN_STORAGE, '');
		write('sessionStorage', REFRESH_TOKEN_STORAGE, '');
	}
}

export const session = new Session();
