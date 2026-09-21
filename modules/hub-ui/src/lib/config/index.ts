export const ACCESS_TOKEN_STORAGE = 'autohub-access-token';
export const REFRESH_TOKEN_STORAGE = 'autohub-refresh-token';
/** Not a secret: remembered so signing in again only asks for the password. */
export const EMAIL_STORAGE = 'autohub-email';
/** The key the UI stored before sessions existed; removed on load so a stale one cannot linger. */
export const LEGACY_API_KEY_STORAGE = 'scheduler-api-key';

export const LOGIN_PATH = '/api/v1/users/login/';
export const REFRESH_PATH = '/api/v1/users/login/refresh';

export function apiBaseUrl(): string {
	if (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) {
		return import.meta.env.VITE_API_BASE_URL;
	}
	return '';
}
