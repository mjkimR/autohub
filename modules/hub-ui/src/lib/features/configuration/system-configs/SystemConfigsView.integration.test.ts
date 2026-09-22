import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { toast } from 'svelte-sonner';
import { afterEach, expect, test, vi } from 'vitest';
import SystemConfigsView from './SystemConfigsView.svelte';

const { api } = vi.hoisted(() => ({ api: { GET: vi.fn() } }));

vi.mock('$lib/api', () => ({ api }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

test('shows each config with its data and reloads on demand', async () => {
	api.GET.mockResolvedValue({
		data: {
			items: [
				{
					id: '0123456789abcdef',
					name: 'dispatcher.heartbeat',
					data: { last_tick_at: '2026-09-21T00:00:00+00:00' },
					created_at: '2026-09-21T00:00:00Z',
					updated_at: '2026-09-21T00:00:00Z'
				}
			]
		}
	});
	const user = userEvent.setup();
	render(SystemConfigsView);

	expect(await screen.findByText('dispatcher.heartbeat')).toBeTruthy();
	expect(screen.getByText(/last_tick_at/)).toBeTruthy();
	expect(screen.getByText('ID: 01234567...')).toBeTruthy();

	await user.click(screen.getByRole('button', { name: 'Refresh' }));
	await waitFor(() => expect(api.GET).toHaveBeenCalledTimes(2));
});

test('an empty list and a failed load are both told', async () => {
	api.GET.mockResolvedValue({ data: { items: [] } });
	render(SystemConfigsView);
	expect(await screen.findByText('No system configurations defined')).toBeTruthy();
	cleanup();

	api.GET.mockRejectedValue(new Error('offline'));
	render(SystemConfigsView);
	await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Failed to load system configs'));
});
