import { cleanup, render, screen, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import SddBatch from './SddBatch.svelte';
import { api } from '$lib/api';
import type { Batch, Preview } from './sdd-batches.svelte';
vi.mock('$lib/api', () => ({ api: { GET: vi.fn(), POST: vi.fn() } }));
afterEach(cleanup);

it('reopens stopped-inflight owner artifacts and retained catalog overrides', async () => {
	const batch: Batch = {
		id: 'batch',
		project_id: 'p',
		state: 'stopped',
		revision: 8,
		exclusion: true,
		detail: 'Admission already in flight',
		basis: { sha: 'initial', project: { repository: 'owner/app' } },
		evaluation: {},
		members: [
			{
				anchor_id: 'PROP-a',
				path: 'docs/proposals/PROP-a/proposal.md',
				state: 'admitted',
				phase: 'dev',
				initial: {
					preferences: {
						planning_effort: 'high',
						dev_effort: 'medium',
						planning_catalog: 'team-a',
						dev_catalog: 'team-b'
					}
				},
				claims: [
					{
						id: 'claim',
						activity: 'dev',
						run_id: 'native-run',
						pull_number: 42,
						branch: 'dev-a',
						initial_sha: 'candidate',
						settled: false
					}
				]
			}
		]
	};
	vi.mocked(api.GET).mockResolvedValue({ data: [batch] } as never);
	render(SddBatch, { projectId: 'p' });
	const user = userEvent.setup();
	await user.click(screen.getByRole('button', { name: 'Load retained batches' }));
	await user.click(await screen.findByText('Inspect retained evidence and preferences'));
	expect(screen.getByRole('link', { name: 'Inspect native owner' }).getAttribute('href')).toContain(
		'run=native-run'
	);
	expect(screen.getByRole('link', { name: 'PR #42' }).getAttribute('href')).toBe(
		'https://github.com/owner/app/pull/42'
	);
	expect(screen.getByText(/Planning catalog: team-a/)).toBeTruthy();
	expect(screen.getByText(/Development catalog: team-b/)).toBeTruthy();
	expect(screen.queryByRole('button', { name: 'Resume future admission' })).toBeNull();
});

it('shows immutable topological confirmation after reverse member selection', async () => {
	const preview = {
		complete: true,
		requested_ref: 'main',
		resolved_sha: 'a'.repeat(40),
		milestone: { id: 'MS-demo' },
		edges: [{ source: 'PROP-b', canonical_id: 'PROP-a' }],
		members: ['PROP-b', 'PROP-a'].map((id) => ({
			id,
			path: `docs/proposals/${id}/proposal.md`,
			activity_kind: 'dev',
			admission: 'pass',
			eligibility: id === 'PROP-a' ? 'eligible_now' : 'held',
			scheduling: id === 'PROP-a' ? 'pass' : 'held',
			workflow_hold: {},
			reasons: id === 'PROP-b' ? ['Waiting on PROP-a'] : []
		}))
	} as unknown as Preview;
	render(SddBatch, { projectId: 'p', preview });
	const user = userEvent.setup();
	await user.click(screen.getByRole('button', { name: 'Open execution selection' }));
	await user.click(screen.getByRole('checkbox', { name: /PROP-b/ }));
	await user.click(screen.getByRole('checkbox', { name: /PROP-a/ }));
	await user.click(screen.getByRole('button', { name: 'Review selection' }));
	const confirm = screen.getByRole('group', { name: 'Confirm future admission' });
	expect(
		within(confirm)
			.getAllByRole('listitem')
			.map((row) => row.textContent?.trim().slice(0, 6))
	).toEqual(['PROP-a', 'PROP-b']);
	vi.mocked(api.POST).mockResolvedValueOnce({
		data: {
			id: 'created',
			project_id: 'p',
			state: 'running',
			revision: 1,
			exclusion: true,
			detail: null,
			basis: {},
			evaluation: {},
			members: []
		}
	} as never);
	await user.click(within(confirm).getByRole('button', { name: 'Confirm create' }));
	const calls = vi.mocked(api.POST).mock.calls as unknown as [
		string,
		{ body: { members: { id: string }[] } }
	][];
	expect(calls.at(-1)?.[1].body.members.map((row) => row.id)).toEqual(['PROP-a', 'PROP-b']);
});
