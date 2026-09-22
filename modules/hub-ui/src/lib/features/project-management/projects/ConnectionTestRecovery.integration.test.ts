import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import type { components } from '$lib/api';
import ConnectionTestRecovery from './ConnectionTestRecovery.svelte';

const { api, toast } = vi.hoisted(() => ({
	api: { POST: vi.fn() },
	toast: { error: vi.fn(), success: vi.fn() }
}));
vi.mock('$lib/api', () => ({ api }));
vi.mock('svelte-sonner', () => ({ toast }));
const probe = {
	id: 't1',
	project_id: 'p1',
	project_revision: 1,
	configuration_current: true,
	repository: 'owner/app',
	ai_catalog_id: null,
	catalog_snapshot: null,
	test_spec: null,
	status: 'canceled',
	phase: 'waiting_for_session',
	cleanup_status: 'waiting',
	cleanup_resolution_available: true,
	detail: null,
	cancel_requested: true,
	evidence: { unconfirmed_pulls: { '43': { sha: 'd'.repeat(40) } } },
	created_at: '2026-09-22T00:00:00Z',
	deadline: '2026-09-22T01:00:00Z',
	finished_at: '2026-09-22T00:05:00Z'
} satisfies components['schemas']['ConnectionTestRead'];
afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

test('requires explicit confirmation and reason, then submits the reviewed PR heads', async () => {
	const user = userEvent.setup();
	const onresolved = vi.fn().mockResolvedValue(undefined);
	api.POST.mockResolvedValue({ data: probe });
	render(ConnectionTestRecovery, { test: probe, onresolved });
	expect(screen.getByRole('link', { name: 'PR #43' }).getAttribute('href')).toBe(
		'https://github.com/owner/app/pull/43'
	);
	await user.click(screen.getByRole('button', { name: 'Review cleanup' }));
	const submit = screen.getByRole('button', {
		name: 'Confirm review and continue cleanup'
	}) as HTMLButtonElement;
	expect(submit.disabled).toBe(true);
	await fireEvent.input(screen.getByLabelText('Review notes'), {
		target: { value: 'Provider history checked' }
	});
	expect(submit.disabled).toBe(true);
	await user.click(screen.getByRole('checkbox'));
	await user.click(submit);
	await waitFor(() => expect(onresolved).toHaveBeenCalledOnce());
	expect(api.POST).toHaveBeenCalledWith(
		'/api/v1/projects/{project_id}/connection-tests/{test_id}/resolve-cleanup',
		expect.objectContaining({
			body: {
				request_id: expect.any(String),
				confirmed_remote_stopped: true,
				note: 'Provider history checked',
				unrelated_pulls: { '43': 'd'.repeat(40) }
			}
		})
	);
});

test('does not silently approve new evidence arriving during review and preserves a rejected form', async () => {
	const user = userEvent.setup();
	const onresolved = vi.fn();
	api.POST.mockResolvedValue({
		response: { status: 409 },
		error: { detail: 'PR evidence changed' }
	});
	const view = render(ConnectionTestRecovery, { test: probe, onresolved });
	await user.click(screen.getByRole('button', { name: 'Review cleanup' }));
	await fireEvent.input(screen.getByLabelText('Review notes'), { target: { value: 'Checked' } });
	await user.click(screen.getByRole('checkbox'));
	await view.rerender({
		test: { ...probe, evidence: { unconfirmed_pulls: { '43': { sha: 'e'.repeat(40) } } } },
		onresolved
	});
	await user.click(screen.getByRole('button', { name: 'Confirm review and continue cleanup' }));
	await waitFor(() => expect(toast.error).toHaveBeenCalled());
	expect(api.POST.mock.calls[0][1].body.unrelated_pulls).toEqual({ '43': 'd'.repeat(40) });
	expect(onresolved).not.toHaveBeenCalled();
	expect((screen.getByLabelText('Review notes') as HTMLTextAreaElement).value).toBe('Checked');
});

test('shows quarantine evidence without offering recovery for unsupported or active tests', () => {
	render(ConnectionTestRecovery, {
		test: { ...probe, cleanup_resolution_available: false },
		onresolved: vi.fn()
	});
	expect(screen.getByRole('link', { name: 'PR #43' })).toBeTruthy();
	expect(screen.queryByRole('button', { name: 'Review cleanup' })).toBeNull();
});
