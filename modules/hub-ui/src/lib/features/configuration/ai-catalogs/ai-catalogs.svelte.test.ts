import { beforeEach, expect, test, vi } from 'vitest';
import { toast } from 'svelte-sonner';
import { AICatalogsState } from './ai-catalogs.svelte';

const { api } = vi.hoisted(() => ({ api: { GET: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));
beforeEach(() => {
	vi.clearAllMocks();
	for (const method of Object.values(api)) method.mockRejectedValue(new TypeError('offline'));
});

test.each(['availability', 'clear', 'enable', 'policy', 'connector'] as const)(
	'network failure during %s leaves the form retryable',
	async (action) => {
		const state = new AICatalogsState();
		const actions = {
			availability: () =>
				state.setAvailability('test', new Date(Date.now() + 3600000).toISOString(), ''),
			clear: () => state.clearAvailability('test'),
			enable: () => state.setEnabled('test', false),
			policy: () =>
				state.updatePolicyConfig('test', {
					daily_task_limit: 10,
					window: 'rolling',
					timezone: 'UTC'
				}),
			connector: () => state.setConnector('test', 'c1')
		};
		await actions[action]();
		expect(toast.error).toHaveBeenCalled();
		expect(toast.success).not.toHaveBeenCalled();
		expect(state.saving).toBe(false);
	}
);
