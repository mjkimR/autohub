import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import SddClaimRecovery from './SddClaimRecovery.svelte';
const { api } = vi.hoisted(() => ({ api: { GET: vi.fn(), POST: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
const claim = {
	id: 'claim-1',
	unit: 'docs/proposals/PROP-demo',
	activity: 'plan',
	run_id: 'old-run',
	checkpoint: { pull_number: 3 },
	checkpoint_digest: 'reviewed-digest',
	retired: true,
	settled: false
};
beforeEach(() => {
	api.GET.mockReset().mockResolvedValue({ data: claim });
	api.POST.mockReset();
});
afterEach(cleanup);
test('releases only the inspected retained reservation after explicit acknowledgment and retries unchanged', async () => {
	api.POST.mockRejectedValueOnce(new Error('Lost acknowledgment response')).mockResolvedValueOnce({
		data: { ...claim, settled: true }
	});
	const onresolved = vi.fn();
	render(SddClaimRecovery, {
		projectId: 'project',
		claimId: 'claim-1',
		repository: 'owner/app',
		onresolved
	});
	const user = userEvent.setup();
	await user.click(screen.getByRole('button', { name: 'Inspect retained owner' }));
	const release = await screen.findByRole('button', { name: 'Release inspected reservation' });
	expect((release as HTMLButtonElement).disabled).toBe(true);
	expect(screen.getByRole('link', { name: 'Open retained Run' }).getAttribute('href')).toBe(
		'/projects/project/runs/old-run'
	);
	await user.click(screen.getByRole('checkbox'));
	await user.click(release);
	await screen.findByText('Lost acknowledgment response');
	expect(onresolved).not.toHaveBeenCalled();
	expect(
		(screen.getByRole('button', { name: 'Inspect retained owner' }) as HTMLButtonElement).disabled
	).toBe(true);
	await user.click(screen.getByRole('button', { name: 'Retry same acknowledgment' }));
	await waitFor(() => expect(onresolved).toHaveBeenCalledOnce());
	expect(api.POST.mock.calls[1]).toEqual(api.POST.mock.calls[0]);
	expect(api.POST.mock.calls[0][1].body).toMatchObject({
		expected_checkpoint_digest: 'reviewed-digest',
		acknowledge_external_work: true
	});
});

test('an expired uncertain optimistic publication can be acknowledged without a Run', async () => {
	api.GET.mockResolvedValue({
		data: {
			...claim,
			retired: false,
			run_id: null,
			checkpoint: { execution_version: 2, uncertain: true, lease_expires_at: null }
		}
	});
	render(SddClaimRecovery, { projectId: 'project', claimId: 'claim-1', onresolved: vi.fn() });
	await userEvent.setup().click(screen.getByRole('button', { name: 'Inspect retained owner' }));
	expect(await screen.findByRole('button', { name: 'Release inspected reservation' })).toBeTruthy();
});

test('a live optimistic publication lease has no release action', async () => {
	api.GET.mockResolvedValue({
		data: {
			...claim,
			retired: false,
			run_id: null,
			checkpoint: {
				execution_version: 2,
				uncertain: true,
				lease_expires_at: '2999-01-01T00:00:00Z'
			}
		}
	});
	render(SddClaimRecovery, { projectId: 'project', claimId: 'claim-1', onresolved: vi.fn() });
	await userEvent.setup().click(screen.getByRole('button', { name: 'Inspect retained owner' }));
	await screen.findByText(/publication lease still owns the work/);
	expect(screen.queryByRole('button', { name: 'Release inspected reservation' })).toBeNull();
});
