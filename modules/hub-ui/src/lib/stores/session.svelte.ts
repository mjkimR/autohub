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

/** Access tokens live only in memory; the server owns the HttpOnly refresh cookie. */
class Session {
	generation = 0;
	accessToken = $state('');
	email = $state(read('localStorage', EMAIL_STORAGE));
	isAuthenticated = $derived(this.accessToken.length > 0);

	constructor() {
		for (const key of [ACCESS_TOKEN_STORAGE, REFRESH_TOKEN_STORAGE, LEGACY_API_KEY_STORAGE]) {
			write('sessionStorage', key, '');
			write('localStorage', key, '');
		}
		if (typeof window !== 'undefined') {
			window.addEventListener('storage', (event) => {
				if (event.key === `${EMAIL_STORAGE}.logout`) this.logout();
			});
		}
	}

	setTokens(tokens: TokenPair) {
		this.generation += 1;
		this.storeTokens(tokens);
	}

	refreshTokens(tokens: TokenPair, generation: number): boolean {
		if (generation !== this.generation) return false;
		this.storeTokens(tokens);
		return true;
	}

	private storeTokens(tokens: TokenPair) {
		this.accessToken = tokens.access_token;
	}

	rememberEmail(email: string) {
		this.email = email;
		write('localStorage', EMAIL_STORAGE, email);
	}

	logout(broadcast = false) {
		this.generation += 1;
		this.accessToken = '';
		if (broadcast)
			write('localStorage', `${EMAIL_STORAGE}.logout`, `${Date.now()}-${Math.random()}`);
	}
}

export const session = new Session();
