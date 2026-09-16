export const API_KEY_HEADER = 'X-API-Key';
export const API_KEY_STORAGE = 'scheduler-api-key';

export function apiBaseUrl(): string {
	if (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) {
		return import.meta.env.VITE_API_BASE_URL;
	}
	return '';
}

export async function hashApiKey(key: string): Promise<string> {
	const trimmed = key.trim();
	if (!trimmed) return '';
	const msgBuffer = new TextEncoder().encode(trimmed);
	const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
	const hashArray = Array.from(new Uint8Array(hashBuffer));
	return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
}
