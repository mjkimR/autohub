export const API_KEY_HEADER = 'X-API-Key';
export const API_KEY_STORAGE = 'scheduler-api-key';

export function apiBaseUrl(): string {
	if (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) {
		return import.meta.env.VITE_API_BASE_URL;
	}
	return '';
}

/**
 * The operator signs in with a password they can remember; its SHA-256 digest is the API key the backend
 * compares verbatim. Hashing here is deliberate and only keeps the password itself out of browser storage and
 * request headers. It is not a hashing-at-rest scheme and adds no strength: the digest is the bearer credential,
 * and guessing is held off by the backend's lockout (modules/hub/app/auth.py). The setup scripts hash the same
 * way, so changing this function locks everyone out.
 */
export async function hashApiKey(key: string): Promise<string> {
	const trimmed = key.trim();
	if (!trimmed) return '';
	const msgBuffer = new TextEncoder().encode(trimmed);
	const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
	const hashArray = Array.from(new Uint8Array(hashBuffer));
	return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
}
