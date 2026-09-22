import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, expect, test, vi } from 'vitest';
import GoogleLogin from './GoogleLogin.svelte';

const { api, session } = vi.hoisted(() => ({
	api: { POST: vi.fn(), GET: vi.fn() },
	session: { setTokens: vi.fn(), rememberEmail: vi.fn() }
}));
vi.mock('$lib/api', () => ({ api }));
vi.mock('$lib/stores/session.svelte', () => ({ session }));

afterEach(() => {
	cleanup();
	vi.resetAllMocks();
	window.history.replaceState({}, '', '/');
});

test('offers Google login only when the server enables it', async () => {
	api.GET.mockResolvedValue({ data: { enabled: true } });
	render(GoogleLogin);
	expect(await screen.findByRole('link', { name: 'Continue with Google' })).toBeTruthy();
});

test('pending registration displays approval guidance without starting a session', async () => {
	window.history.replaceState({}, '', '/?google=complete');
	api.GET.mockResolvedValue({ data: { enabled: true } });
	api.POST.mockResolvedValue({
		data: { status: 'pending', email: 'new@example.com', tokens: null }
	});
	render(GoogleLogin);
	expect(await screen.findByText(/awaiting administrator approval/)).toBeTruthy();
	expect(session.setTokens).not.toHaveBeenCalled();
	expect(window.location.search).toBe('');
});

test('approved exchange starts the existing session store', async () => {
	window.history.replaceState({}, '', '/?google=complete');
	const tokens = { access_token: 'access', refresh_token: 'refresh' };
	api.POST.mockResolvedValue({ data: { status: 'approved', email: 'new@example.com', tokens } });
	render(GoogleLogin);
	await waitFor(() => expect(session.setTokens).toHaveBeenCalledWith(tokens));
	expect(api.POST).toHaveBeenCalledExactlyOnceWith('/api/v1/auth/google/exchange');
});

test('an existing email collision requires the existing login', async () => {
	window.history.replaceState({}, '', '/?google=existing_account');
	api.GET.mockResolvedValue({ data: { enabled: true } });
	render(GoogleLogin);
	expect(await screen.findByText(/not linked automatically/)).toBeTruthy();
	expect(api.POST).not.toHaveBeenCalled();
	expect(session.setTokens).not.toHaveBeenCalled();
});
