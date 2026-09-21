import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import WebhookDeliveriesView from './WebhookDeliveriesView.svelte';

const { api } = vi.hoisted(() => ({ api: { GET: vi.fn() } }));

vi.mock('$lib/api', () => ({ api }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

const skipped = {
	id: 'd1',
	delivery_id: 'gh-1',
	event: 'issue_comment',
	repository: 'owner/app',
	pull_number: 7,
	auto_run: true,
	requested_catalog: 'jules',
	status: 'processed',
	attempts: 2,
	processed_at: '2026-09-21T00:00:00Z',
	failure_detail: "Enrollment skipped: AI catalog 'jules' cannot deliver pull request work",
	created_at: '2026-09-21T00:00:00Z',
	updated_at: '2026-09-21T00:00:00Z'
};

beforeEach(() => {
	api.GET.mockResolvedValue({ data: { items: [skipped], total_count: 1 } });
});

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

test('shows why a trigger did not enroll and filters the log', async () => {
	const user = userEvent.setup();
	render(WebhookDeliveriesView);

	expect(await screen.findByText(/Enrollment skipped/)).toBeTruthy();
	expect(screen.getByText('@auto-run:jules')).toBeTruthy();
	expect(screen.getByText('owner/app#7')).toBeTruthy();
	expect(screen.getByText('×2')).toBeTruthy();
	// Routine deliveries are hidden until asked for.
	expect(api.GET).toHaveBeenCalledWith('/api/v1/github-webhook-deliveries', {
		params: { query: { offset: 0, limit: 50, noteworthy: true } }
	});

	await user.click(screen.getByRole('checkbox', { name: 'Only triggers and problems' }));
	await user.selectOptions(screen.getByRole('combobox', { name: 'Status' }), 'failed');

	await waitFor(() =>
		expect(api.GET).toHaveBeenLastCalledWith('/api/v1/github-webhook-deliveries', {
			params: { query: { offset: 0, limit: 50, noteworthy: false, status: 'failed' } }
		})
	);
});
