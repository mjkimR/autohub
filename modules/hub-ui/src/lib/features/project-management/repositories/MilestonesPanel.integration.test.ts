import { cleanup, fireEvent, render, screen, within } from '@testing-library/svelte';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import MilestonesPanel from './MilestonesPanel.svelte';
import { sourceFor } from './documents/fixtures';

const { api, goto } = vi.hoisted(() => ({ api: { GET: vi.fn() }, goto: vi.fn() }));
vi.mock('$lib/api', () => ({ api }));
vi.mock('$app/navigation', () => ({ goto }));
beforeEach(() => {
	api.GET.mockReset();
	goto.mockReset();
	api.GET.mockResolvedValue({
		data: {
			items: [
				{
					id: 'run-1',
					state: 'paused',
					pull_number: 9,
					sdd_snapshot: { spec_dir: 'docs/proposals/PROP-live', activity_kind: 'plan' }
				}
			],
			total_count: 1
		}
	});
});
afterEach(cleanup);

const project = { id: 'p1', project_type: 'sdd' } as never;

test('lists only open milestones with their members and opens a member in the Repository tab', async () => {
	const dataSource = sourceFor({
		'docs/roadmap/MS-live.md': '---\nid: MS-live\ntitle: Live work\nstatus: active\n---\n# L',
		'docs/roadmap/MS-later.md': '---\nid: MS-later\ntitle: Later work\nstatus: planned\n---\n# P',
		'docs/roadmap/_archive/MS-old.md': '---\nid: MS-old\ntitle: Old work\nstatus: done\n---\n# O',
		'docs/proposals/PROP-live/proposal.md':
			'---\nid: PROP-live\ntitle: Live proposal\nstatus: accepted\nmilestone: MS-live\n---\n# P',
		'docs/proposals/PROP-loose/proposal.md': '---\nid: PROP-loose\ntitle: Loose\n---\n# L',
		'specs/2026-11/20261117-x/spec.md': '---\nid: SPEC-x\ntitle: A spec\n---\n# S'
	});
	render(MilestonesPanel, { project, dataSource });

	const live = await screen.findByRole('region', { name: 'Live work' });
	expect(screen.getByRole('region', { name: 'Later work' })).toBeTruthy();
	expect(screen.queryByText('Old work')).toBeNull();
	expect(screen.queryByText('Loose')).toBeNull();
	expect(screen.queryByText('A spec')).toBeNull();
	expect(await within(live).findByText('Paused')).toBeTruthy();
	expect(dataSource.tree).not.toHaveBeenCalledWith('specs', 'main', expect.any(AbortSignal));

	await fireEvent.click(within(live).getByRole('button', { name: 'Live proposal' }));
	expect(goto).toHaveBeenCalledWith(
		'/projects/p1?tab=repository&path=docs%2Fproposals%2FPROP-live%2Fproposal.md&ref=main'
	);
});

test('a repository without open milestones says where they come from', async () => {
	render(MilestonesPanel, { project, dataSource: sourceFor({ 'docs/README.md': '# R' }) });
	expect(await screen.findByText(/No open milestones on this branch/)).toBeTruthy();
});
