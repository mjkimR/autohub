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
	run_id: null,
	checkpoint: { pull_number: 3, uncertain: true },
	checkpoint_digest: 'reviewed-digest',
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
	const release = await screen.findByRole('button', { name: 'Release inspected reservation' });
	expect((release as HTMLButtonElement).disabled).toBe(true);

	await user.click(screen.getByRole('checkbox'));
	await user.click(release);
	await screen.findByText(/Lost acknowledgment response/);
	expect(onresolved).not.toHaveBeenCalled();
	expect(
		(screen.getByRole('button', { name: 'Inspect again' }) as HTMLButtonElement).disabled
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
			run_id: null
		}
	});
	render(SddClaimRecovery, { projectId: 'project', claimId: 'claim-1', onresolved: vi.fn() });
	expect(await screen.findByRole('button', { name: 'Release inspected reservation' })).toBeTruthy();
	expect(screen.getByRole('heading').textContent?.replace(/\s+/g, ' ')).toContain(
		'Planning for docs/proposals/PROP-demo has an uncertain reservation'
	);
	expect(screen.queryByText(/\bplan\b/)).toBeNull();
});

test('a live optimistic publication lease has no release action', async () => {
	api.GET.mockResolvedValue({
		data: {
			...claim,
			run_id: null,
			checkpoint: {
				uncertain: true,
				lease_expires_at: '2999-01-01T00:00:00Z'
			}
		}
	});
	render(SddClaimRecovery, { projectId: 'project', claimId: 'claim-1', onresolved: vi.fn() });
	await screen.findByText(/publication lease still owns the work/);
	expect(screen.queryByRole('button', { name: 'Release inspected reservation' })).toBeNull();
});

test('a publication lease that ends while the card is open turns releasable without a reload', async () => {
	vi.useFakeTimers({ shouldAdvanceTime: true });
	try {
		api.GET.mockResolvedValue({
			data: {
				...claim,
				checkpoint: {
					uncertain: true,
					lease_expires_at: new Date(Date.now() + 5_000).toISOString()
				}
			}
		});
		render(SddClaimRecovery, { projectId: 'project', claimId: 'claim-1', onresolved: vi.fn() });
		await screen.findByText(/publication lease still owns the work/);
		expect(screen.queryByRole('button', { name: 'Release inspected reservation' })).toBeNull();
		await vi.advanceTimersByTimeAsync(6_000);
		expect(
			await screen.findByRole('button', { name: 'Release inspected reservation' })
		).toBeTruthy();
		expect(api.GET).toHaveBeenCalledOnce();
	} finally {
		vi.useRealTimers();
	}
});

test('a failed evidence read is plain and retryable', async () => {
	api.GET.mockResolvedValueOnce({ error: { detail: 'Internal Server Error' } });
	render(SddClaimRecovery, { projectId: 'project', claimId: 'claim-1', onresolved: vi.fn() });
	const alert = await screen.findByRole('alert');
	expect(alert.textContent).toContain("Couldn't load the retained owner");
	expect(alert.textContent).not.toContain('Internal Server Error');
	await userEvent.setup().click(screen.getByRole('button', { name: 'Inspect again' }));
	expect(await screen.findByRole('button', { name: 'Release inspected reservation' })).toBeTruthy();
});
