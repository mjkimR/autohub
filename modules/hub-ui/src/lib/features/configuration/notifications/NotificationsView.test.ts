import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { toast } from 'svelte-sonner';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import NotificationsView from './NotificationsView.svelte';

const { api } = vi.hoisted(() => ({
	api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() }
}));

vi.mock('$lib/api', () => ({ api }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

const phone = {
	id: 'n1',
	name: 'My phone',
	kind: 'telegram',
	enabled: true,
	chat_id: '424242',
	last_sent_at: null,
	last_error: 'Telegram returned HTTP 400: Bad Request: chat not found'
};

beforeEach(() => {
	api.GET.mockResolvedValue({ data: { items: [] } });
	api.POST.mockResolvedValue({ data: { ...phone, last_error: null } });
	api.PATCH.mockResolvedValue({ data: phone });
});

afterEach(() => {
	cleanup();
	document.body.style.removeProperty('pointer-events');
	vi.clearAllMocks();
});

test('explains the setup when no channel exists and adds a Telegram channel', async () => {
	const user = userEvent.setup();
	render(NotificationsView);
	expect(await screen.findByText(/the hub stops silently/)).toBeTruthy();

	await user.click(screen.getByRole('button', { name: 'Add Telegram channel' }));
	await user.type(screen.getByLabelText('Name'), 'My phone');
	await user.type(screen.getByLabelText('Chat ID'), ' 424242 ');
	await user.type(screen.getByLabelText('Bot token'), '123:secret');
	await user.click(screen.getByRole('button', { name: 'Save' }));

	await waitFor(() =>
		expect(api.POST).toHaveBeenCalledWith('/api/v1/notification-channels', {
			body: {
				name: 'My phone',
				kind: 'telegram',
				enabled: true,
				chat_id: '424242',
				bot_token: '123:secret'
			}
		})
	);
});

test('shows the last failure, reports an undelivered test, and keeps the token on edit', async () => {
	api.GET.mockResolvedValue({ data: { items: [phone] } });
	api.POST.mockResolvedValue({ data: { delivered: false, detail: 'Telegram request failed' } });
	const user = userEvent.setup();
	render(NotificationsView);
	expect(await screen.findByText(/chat not found/)).toBeTruthy();

	await user.click(screen.getByRole('button', { name: 'Send test' }));
	await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Telegram request failed'));
	expect(api.POST).toHaveBeenCalledWith('/api/v1/notification-channels/{channel_id}/test', {
		params: { path: { channel_id: 'n1' } }
	});

	await user.click(screen.getByRole('button', { name: 'Edit' }));
	await user.type(screen.getByLabelText('Chat ID'), '99');
	await user.click(screen.getByRole('button', { name: 'Save' }));

	await waitFor(() =>
		expect(api.PATCH).toHaveBeenCalledWith('/api/v1/notification-channels/{channel_id}', {
			params: { path: { channel_id: 'n1' } },
			body: { name: 'My phone', chat_id: '42424299' }
		})
	);
});
