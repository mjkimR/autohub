import { afterEach, expect, test, vi } from 'vitest';

const storage = () => {
	const values = new Map<string, string>();
	return {
		getItem: (key: string) => values.get(key) ?? null,
		setItem: (key: string, value: string) => values.set(key, value),
		removeItem: (key: string) => values.delete(key)
	};
};

afterEach(() => {
	vi.unstubAllGlobals();
	vi.resetModules();
});

test('legacy tokens are removed and new tokens never enter browser storage', async () => {
	vi.resetModules();
	const tab = storage();
	const persistent = storage();
	for (const target of [tab, persistent]) {
		target.setItem('autohub-access-token', 'legacy-access');
		target.setItem('autohub-refresh-token', 'legacy-refresh');
	}
	vi.stubGlobal('sessionStorage', tab);
	vi.stubGlobal('localStorage', persistent);
	const { session } = await import('./session.svelte');
	expect(session.isAuthenticated).toBe(false);
	session.setTokens({ access_token: 'fresh', refresh_token: 'must-not-be-stored' });
	expect(session.accessToken).toBe('fresh');
	for (const target of [tab, persistent]) {
		expect(target.getItem('autohub-access-token')).toBeNull();
		expect(target.getItem('autohub-refresh-token')).toBeNull();
	}
});
