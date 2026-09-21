import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
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
	min_level: 'info' as const,
	chat_id: '424242',
	created_at: '2026-09-21T00:00:00Z',
	updated_at: '2026-09-21T00:00:00Z',
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
	// Set in one step: the dialog moves focus while it opens, which drops keystrokes typed one by one.
	await fireEvent.input(screen.getByLabelText('Name'), { target: { value: 'My phone' } });
	await fireEvent.input(screen.getByLabelText('Chat ID'), { target: { value: ' 424242 ' } });
	await fireEvent.input(screen.getByLabelText('Bot token'), { target: { value: '123:secret' } });
	await user.click(screen.getByRole('button', { name: 'Save' }));

	await waitFor(() =>
		expect(api.POST).toHaveBeenCalledWith('/api/v1/notification-channels', {
			body: {
				name: 'My phone',
				kind: 'telegram',
				enabled: true,
				min_level: 'info',
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
	await fireEvent.input(screen.getByLabelText('Chat ID'), { target: { value: '-100777' } });
	await user.click(screen.getByRole('button', { name: 'Save' }));

	await waitFor(() =>
		expect(api.PATCH).toHaveBeenCalledWith('/api/v1/notification-channels/{channel_id}', {
			params: { path: { channel_id: 'n1' } },
			body: { name: 'My phone', min_level: 'info', chat_id: '-100777' }
		})
	);
});

test('a load failure offers retry instead of displaying the onboarding empty state', async () => {
	api.GET.mockResolvedValue({ error: { detail: 'Unavailable' } });
	const user = userEvent.setup();
	render(NotificationsView);
	expect(await screen.findByRole('alert')).toBeTruthy();
	expect(screen.queryByText(/the hub stops silently/)).toBeNull();
	api.GET.mockResolvedValue({ data: { items: [phone] } });
	await user.click(screen.getByRole('button', { name: 'Retry' }));
	expect(await screen.findByText('My phone')).toBeTruthy();
});

test('a disconnected save keeps the entered form open', async () => {
	api.POST.mockRejectedValue(new TypeError('offline'));
	const user = userEvent.setup();
	render(NotificationsView);
	await user.click(screen.getByRole('button', { name: 'Add Telegram channel' }));
	await fireEvent.input(screen.getByLabelText('Name'), { target: { value: 'Phone' } });
	await fireEvent.input(screen.getByLabelText('Chat ID'), { target: { value: '42' } });
	await fireEvent.input(screen.getByLabelText('Bot token'), { target: { value: 'test-token' } });
	await user.click(screen.getByRole('button', { name: 'Save' }));
	await waitFor(() =>
		expect(toast.error).toHaveBeenCalledWith('Request failed. Check your connection and retry.')
	);
	expect((screen.getByLabelText('Name') as HTMLInputElement).value).toBe('Phone');
	expect((screen.getByRole('button', { name: 'Save' }) as HTMLButtonElement).disabled).toBe(false);
});
