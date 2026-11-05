import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import WorkItemRecovery from './WorkItemRecovery.svelte';
import type { components } from '$lib/api';

const { api } = vi.hoisted(() => ({ api: { GET: vi.fn(), POST: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
const item = {
	id: 'i1',
	key: 'build',
	state: 'failed',
	detail: 'Stopped',
	pull_url: 'https://github.com/o/r/pull/1',
	recovery: {
		eligible: true,
		reason: 'eligible',
		next_action: 'Review',
		run_revision: 4,
		pending_state: null
	}
} as components['schemas']['WorkItemRead'];
const record = {
	id: 'r1',
	request_id: 'request1',
	actor: 'user:operator',
	reason: 'Repaired',
	state: 'awaiting-admission',
	detail: 'Waiting for capacity',
	created_at: '2026-11-05T00:00:00Z',
	prior_outcome: { state: 'failed', pipeline_run_id: 'run1' },
	events: [{ id: 'e1', kind: 'accepted', detail: 'Accepted' }]
};
const refresh = vi.fn();
beforeEach(() => {
	sessionStorage.clear();
	api.GET.mockReset().mockResolvedValue({ data: { items: [record], total_count: 1 } });
	api.POST.mockReset().mockResolvedValue({ data: { recovery: record, item } });
	refresh.mockReset().mockResolvedValue(undefined);
});
afterEach(cleanup);
function mount(selected = item) {
	return render(WorkItemRecovery, {
		projectId: 'p1',
		planId: 'plan1',
		revision: 3,
		baseBranch: 'main',
		item: selected,
		refresh
	});
}
async function confirm() {
	await fireEvent.click(screen.getByRole('button', { name: 'Retry Work Item' }));
	await fireEvent.input(screen.getByLabelText('Recovery reason'), {
		target: { value: 'Repaired' }
	});
	await fireEvent.click(screen.getByRole('button', { name: 'Confirm retry' }));
}
test('requires a reason and shows retained work before sending the command', async () => {
	mount();
	await fireEvent.click(screen.getByRole('button', { name: 'Retry Work Item' }));
	expect(screen.getByText(/Successful Work Items stay complete/)).toBeTruthy();
	expect(
		(screen.getByRole('button', { name: 'Confirm retry' }) as HTMLButtonElement).disabled
	).toBe(true);
	await fireEvent.input(screen.getByLabelText('Recovery reason'), {
		target: { value: 'Repaired' }
	});
	await fireEvent.click(screen.getByRole('button', { name: 'Confirm retry' }));
	await waitFor(() => expect(refresh).toHaveBeenCalled());
	expect(api.POST.mock.calls[0][1].body).toMatchObject({
		reason: 'Repaired',
		expected_revision: 3,
		expected_run_revision: 4
	});
	expect(await screen.findByText(/Recovery awaiting-admission: Waiting for capacity/)).toBeTruthy();
});
test('response loss replays the same immutable request across remount', async () => {
	api.POST.mockRejectedValueOnce(new TypeError('Response lost'));
	const mounted = mount();
	await confirm();
	await screen.findByRole('alert');
	const first = api.POST.mock.calls[0];
	mounted.unmount();
	mount();
	await fireEvent.click(screen.getByRole('button', { name: 'Retry Work Item' }));
	await fireEvent.click(screen.getAllByRole('button', { name: 'Check original request' })[0]);
	await waitFor(() => expect(api.POST).toHaveBeenCalledTimes(2));
	expect(api.POST.mock.calls[1]).toEqual(first);
});
test('ineligible Items explain the next action and preserve paged history', async () => {
	mount({
		...item,
		recovery: {
			...item.recovery!,
			eligible: false,
			reason: 'run_paused',
			next_action: 'Open existing Run controls'
		}
	});
	expect(screen.queryByRole('button', { name: 'Retry Work Item' })).toBeNull();
	expect(screen.getByText(/Open existing Run controls/)).toBeTruthy();
	await fireEvent.click(screen.getByRole('button', { name: 'Inspect recovery history' }));
	expect(await screen.findByText(/Previous result: failed/)).toBeTruthy();
	expect(screen.getByRole('link', { name: 'Original execution' }).getAttribute('href')).toContain(
		'run1'
	);
	expect(api.POST).not.toHaveBeenCalled();
});

test('shows the pending hold reason after remount rather than the previous failure', () => {
	mount({
		...item,
		detail: 'Previous delivery failed',
		recovery: {
			...item.recovery!,
			eligible: false,
			pending_state: 'awaiting-admission',
			pending_detail: 'Waiting for AI catalog capacity'
		}
	});
	expect(screen.getByRole('status').textContent).toContain('Waiting for AI catalog capacity');
	expect(screen.getByRole('status').textContent).not.toContain('Previous delivery failed');
});
