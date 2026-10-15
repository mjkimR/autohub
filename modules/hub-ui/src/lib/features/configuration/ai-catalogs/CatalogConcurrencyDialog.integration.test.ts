import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { toast } from 'svelte-sonner';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import AICatalogsView from './AICatalogsView.svelte';

const { api } = vi.hoisted(() => ({
	api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() }
}));

vi.mock('$lib/api', () => ({ api }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

const codex = {
	id: 'c1',
	key: 'personal-codex',
	name: 'Personal Codex',
	kind: 'codex',
	adapter: 'codex-github-mention',
	enabled: true,
	availability_state: 'normal',
	available_at: null,
	availability_source: null,
	availability_note: null,
	configured_concurrency: 1,
	effective_concurrency: 1,
	active_dispatch_count: 1,
	held_run_count: 1,
	open_session_count: 0,
	connector_id: null,
	connector_provider: null,
	pipeline_delivery: true,
	session_work_types: [],
	policy_config: {},
	policy_state: {}
};

beforeEach(() => {
	vi.clearAllMocks();
	api.GET.mockImplementation((path: string) =>
		Promise.resolve({ data: { items: path === '/api/v1/connectors' ? [] : [codex] } })
	);
	api.PUT.mockResolvedValue({ data: { ...codex, configured_concurrency: 2 } });
});

afterEach(() => {
	cleanup();
	document.body.style.removeProperty('pointer-events');
});

test('changes the concurrent work limit of an existing catalog', async () => {
	const user = userEvent.setup();
	render(AICatalogsView);
	await screen.findByText('Personal Codex');

	await user.click(screen.getByRole('button', { name: 'Concurrency' }));
	const input = screen.getByLabelText('Concurrent work limit');
	expect((input as HTMLInputElement).value).toBe('1');
	await user.clear(input);
	await user.type(input, '2');
	await user.click(screen.getByRole('button', { name: 'Save limit' }));

	await waitFor(() =>
		expect(api.PUT).toHaveBeenCalledWith('/api/v1/ai-catalogs/{catalog_key}/concurrency', {
			params: { path: { catalog_key: 'personal-codex' } },
			body: { configured_concurrency: 2 }
		})
	);
	expect(toast.success).toHaveBeenCalledWith('AI catalog concurrent work limit updated');
});

test('keeps the dialog open when the limit is out of range', async () => {
	const user = userEvent.setup();
	render(AICatalogsView);
	await screen.findByText('Personal Codex');

	await user.click(screen.getByRole('button', { name: 'Concurrency' }));
	const input = screen.getByLabelText('Concurrent work limit');
	await user.clear(input);
	await user.type(input, '0');
	await user.click(screen.getByRole('button', { name: 'Save limit' }));

	expect(api.PUT).not.toHaveBeenCalled();
	expect(screen.getByRole('button', { name: 'Save limit' })).toBeTruthy();
});
