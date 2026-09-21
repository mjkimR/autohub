import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import LoginView from './LoginView.svelte';

const { api, session } = vi.hoisted(() => ({
	api: { GET: vi.fn() },
	session: { setApiKey: vi.fn() }
}));

vi.mock('$lib/api', () => ({ api }));
vi.mock('$lib/stores/session.svelte', () => ({ session }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

// SHA-256 of "my password": the digest, never the password, is what is sent and stored.
const DIGEST = 'bb14292d91c6d0920a5536bb41f3a50f66351b7b9d94c804dfce8a96ca1051f2';

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

async function signIn(password: string) {
	const user = userEvent.setup();
	render(LoginView);
	await fireEvent.input(screen.getByPlaceholderText('Enter secret API key'), {
		target: { value: password }
	});
	await user.click(screen.getByRole('button', { name: /sign in|authenticate|connect|login/i }));
}

test('sends and stores the digest of the password, never the password', async () => {
	api.GET.mockResolvedValue({ data: [], response: new Response(null, { status: 200 }) });

	await signIn(' my password ');

	await waitFor(() => expect(session.setApiKey).toHaveBeenCalledWith(DIGEST));
	expect(api.GET).toHaveBeenCalledWith('/api/v1/tasks/specs', { headers: { 'X-API-Key': DIGEST } });
	expect(JSON.stringify(api.GET.mock.calls)).not.toContain('my password');
});

test('a wrong key and a lockout are told apart', async () => {
	api.GET.mockResolvedValue({ error: {}, response: new Response(null, { status: 401 }) });
	await signIn('wrong');
	expect(await screen.findByText(/check your API key/)).toBeTruthy();
	expect(session.setApiKey).not.toHaveBeenCalled();
	cleanup();

	api.GET.mockResolvedValue({
		error: {},
		response: new Response(null, { status: 429, headers: { 'Retry-After': '240' } })
	});
	await signIn('my password');
	expect(await screen.findByText(/Try again in 4 minute/)).toBeTruthy();
	expect(session.setApiKey).not.toHaveBeenCalled();
});
