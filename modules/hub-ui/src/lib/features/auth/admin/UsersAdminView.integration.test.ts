import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import UsersAdminView from './UsersAdminView.svelte';

const { api } = vi.hoisted(() => ({ api: { POST: vi.fn(), GET: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));
afterEach(() => {
	cleanup();
	vi.resetAllMocks();
});

test('a regular user cannot load the account list', async () => {
	api.GET.mockResolvedValue({ data: { id: 'regular', is_superadmin: false } });
	render(UsersAdminView);
	expect(await screen.findByRole('alert')).toHaveProperty(
		'textContent',
		'Administrator access is required.'
	);
	expect(api.GET).toHaveBeenCalledExactlyOnceWith('/api/v1/users/me');
});

test('approval requires confirmation and sends the reviewed account version', async () => {
	const pending = {
		id: 'pending',
		email: 'new@example.com',
		approval_status: 'pending',
		auth_version: 4,
		is_active: true,
		is_superadmin: false
	};
	api.GET.mockImplementation((path) =>
		Promise.resolve({
			data: path.endsWith('/me')
				? { id: 'admin', is_superadmin: true }
				: { items: [pending], last: true }
		})
	);
	api.POST.mockResolvedValue({
		data: { ...pending, approval_status: 'approved' },
		response: new Response()
	});
	const user = userEvent.setup();
	render(UsersAdminView);
	await user.click(await screen.findByRole('button', { name: 'Approve' }));
	expect(api.POST).not.toHaveBeenCalled();
	await user.type(screen.getByLabelText('Reason (optional)'), 'Personal repository access');
	await user.click(screen.getByRole('button', { name: 'Confirm change' }));
	await waitFor(() =>
		expect(api.POST).toHaveBeenCalledWith('/api/v1/users/admin/{user_id}/access', {
			params: { path: { user_id: 'pending' } },
			body: { action: 'approve', expected_version: 4, reason: 'Personal repository access' }
		})
	);
});
