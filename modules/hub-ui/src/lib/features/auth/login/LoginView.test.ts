import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import LoginView from './LoginView.svelte';

const { api, session } = vi.hoisted(() => ({
	api: { POST: vi.fn() },
	session: { email: 'operator@example.com', setTokens: vi.fn(), rememberEmail: vi.fn() }
}));

vi.mock('$lib/api', () => ({ api }));
vi.mock('$lib/stores/session.svelte', () => ({ session }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

async function signIn(password: string) {
	const user = userEvent.setup();
	render(LoginView);
	await fireEvent.input(screen.getByLabelText('Password'), { target: { value: password } });
	await user.click(screen.getByRole('button', { name: 'Sign in' }));
}

test('signs in with the remembered email and keeps only the tokens', async () => {
	const tokens = { access_token: 'access', refresh_token: 'refresh', token_type: 'bearer' };
	api.POST.mockResolvedValue({ data: tokens, response: new Response(null, { status: 200 }) });

	await signIn('operator-password');

	await waitFor(() => expect(session.setTokens).toHaveBeenCalledWith(tokens));
	expect(session.rememberEmail).toHaveBeenCalledWith('operator@example.com');
	const [path, request] = api.POST.mock.calls[0];
	expect(path).toBe('/api/v1/users/login/');
	// An OAuth2 password form, not JSON.
	expect(request.bodySerializer(request.body).toString()).toBe(
		'username=operator%40example.com&password=operator-password&scope='
	);
	// The password is only ever held by the form, and is cleared once it has been used.
	expect((screen.getByLabelText('Password') as HTMLInputElement).value).toBe('');
	expect(JSON.stringify(session.setTokens.mock.calls)).not.toContain('operator-password');
});

test('a wrong password and a lockout are told apart', async () => {
	api.POST.mockResolvedValue({ error: {}, response: new Response(null, { status: 400 }) });
	await signIn('wrong');
	expect(await screen.findByText(/Check your email and password/)).toBeTruthy();
	expect(session.setTokens).not.toHaveBeenCalled();
	cleanup();

	api.POST.mockResolvedValue({
		error: {},
		response: new Response(null, { status: 429, headers: { 'Retry-After': '240' } })
	});
	await signIn('operator-password');
	expect(await screen.findByText(/Try again in 4 minute/)).toBeTruthy();
	expect(session.setTokens).not.toHaveBeenCalled();
});
