import { beforeEach, expect, test, vi } from 'vitest';
import { toast } from 'svelte-sonner';
import { NotificationChannelsState } from './notifications.svelte';

const { api } = vi.hoisted(() => ({
	api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() }
}));
vi.mock('$lib/api', () => ({ api }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));
beforeEach(() => {
	vi.clearAllMocks();
	for (const method of Object.values(api)) method.mockRejectedValue(new TypeError('offline'));
});

test.each(['create', 'update', 'setEnabled', 'remove', 'sendTest'] as const)(
	'network failure during %s is handled and allows retry',
	async (action) => {
		const state = new NotificationChannelsState();
		const form = { name: 'Phone', chatId: '42', botToken: 'test-token', minLevel: 'info' as const };
		const actions = {
			create: () => state.create(form),
			update: () => state.update('n1', form),
			setEnabled: () => state.setEnabled('n1', false),
			remove: () => state.remove('n1'),
			sendTest: () => state.sendTest('n1')
		};
		await actions[action]();
		expect(toast.error).toHaveBeenCalled();
		expect(toast.success).not.toHaveBeenCalled();
		expect(state.saving).toBe(false);
		expect(state.testingId).toBeNull();
	}
);

test('HTTP failure retains the last successful channel list and is cleared after retry', async () => {
	const state = new NotificationChannelsState();
	api.GET.mockResolvedValueOnce({ data: { items: [{ id: 'n1', name: 'Phone' }] } });
	await state.load();
	api.GET.mockResolvedValueOnce({ error: { detail: 'Unavailable' } });
	await state.load();
	expect(state.items[0].id).toBe('n1');
	expect(state.error).toBeTruthy();
	api.GET.mockResolvedValueOnce({ data: { items: [] } });
	await state.load();
	expect(state.items).toEqual([]);
	expect(state.error).toBe('');
});
