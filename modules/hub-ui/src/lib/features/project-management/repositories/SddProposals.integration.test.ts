import { cleanup, render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import SddProposals from './SddProposals.svelte';

const { api } = vi.hoisted(() => ({ api: { POST: vi.fn(), GET: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
const proposal = (overrides: Record<string, unknown>) => ({
	slug: 'demo',
	id: 'PROP-demo',
	path: 'docs/proposals/PROP-demo',
	title: 'Demo',
	status: 'draft',
	display_status: 'draft',
	task_kind: 'feature',
	plan_branch: false,
	dev_branch: false,
	plan_pull: null,
	dev_pull: null,
	run: null,
	actions: [],
	note: null,
	...overrides
});
const listed = (items: unknown[]) => ({
	data: { base_branch: 'main', base_sha: 'b'.repeat(40), items, truncated: false }
});
beforeEach(() => {
	api.POST.mockReset().mockResolvedValue({ data: { id: 'run' } });
	api.GET.mockReset();
});
afterEach(cleanup);

test('starts review of a draft and development of an accepted proposal on the chosen base', async () => {
	const user = userEvent.setup();
	api.GET.mockResolvedValue(
		listed([
			proposal({ actions: ['start_planning'] }),
			proposal({
				slug: 'next',
				id: 'PROP-next',
				title: 'Next',
				status: 'accepted',
				actions: ['start_development']
			})
		])
	);
	render(SddProposals, { projectId: 'p1', repository: 'owner/app' });
	await user.click(await screen.findByRole('button', { name: 'Start review' }));
	expect(api.POST.mock.calls[0][0]).toBe(
		'/api/v1/projects/{project_id}/sdd/proposals/{slug}/planning'
	);
	expect(api.POST.mock.calls[0][1]).toMatchObject({
		params: { path: { project_id: 'p1', slug: 'demo' } },
		body: { base_branch: 'main' }
	});
	expect(api.POST.mock.calls[0][1].body).not.toHaveProperty('activity_effort');
	await user.selectOptions(screen.getByLabelText('Proposal activity effort'), 'high');
	await user.click(screen.getByRole('button', { name: 'Start development' }));
	expect(api.POST.mock.calls[1][0]).toBe(
		'/api/v1/projects/{project_id}/sdd/proposals/{slug}/development'
	);
	expect(api.POST.mock.calls[1][1].body).toMatchObject({ activity_effort: 'high' });
});

test('accept opens the evidence review while rejection records the head and a required reason', async () => {
	const user = userEvent.setup();
	const run = {
		id: 'r1',
		state: 'blocked',
		revision: 4,
		pause_reason: 'x',
		pull_number: 7,
		head_sha: 'a'.repeat(40),
		plan_accept_open: true,
		decided: false
	};
	api.GET.mockResolvedValue(
		listed([
			proposal({ display_status: 'reviewing', plan_pull: 7, run, actions: ['accept', 'reject'] })
		])
	);
	render(SddProposals, { projectId: 'p1', repository: 'owner/app' });
	expect((await screen.findByRole('link', { name: /plan-demo #7/ })).getAttribute('href')).toBe(
		'https://github.com/owner/app/pull/7'
	);
	expect(screen.getByRole('link', { name: 'Review & accept' }).getAttribute('href')).toBe(
		'/projects/runs?run=r1&view=decisions'
	);
	expect(api.POST).not.toHaveBeenCalled();
	await user.click(screen.getByRole('button', { name: 'Reject…' }));
	const reject = screen.getByRole('button', { name: 'Reject proposal' }) as HTMLButtonElement;
	expect(reject.disabled).toBe(true);
	await user.type(screen.getByLabelText(/Rejection reason/), 'Too broad');
	await user.click(reject);
	expect(api.POST.mock.calls[0][1].body).toMatchObject({
		decision: 'reject_plan',
		expected_revision: 4,
		head_sha: 'a'.repeat(40),
		feedback: 'Too broad'
	});
});

test('a rejected proposal shows that it waits for hygiene and offers no action', async () => {
	api.GET.mockResolvedValue(
		listed([
			proposal({
				status: 'rejected',
				display_status: 'rejected',
				note: 'Planning ended by rejection; hygiene'
			})
		])
	);
	render(SddProposals, { projectId: 'p1' });
	expect(await screen.findByText(/Planning ended by rejection/)).toBeTruthy();
	expect(screen.queryAllByRole('button').map((b) => b.textContent?.trim())).toEqual(['Refresh']);
});

test('a failed start is reported and the list stays', async () => {
	const user = userEvent.setup();
	api.GET.mockResolvedValue(listed([proposal({ actions: ['start_planning'] })]));
	api.POST.mockResolvedValueOnce({
		error: { detail: 'Branch plan-demo already exists on the remote' }
	});
	render(SddProposals, { projectId: 'p1' });
	await user.click(await screen.findByRole('button', { name: 'Start review' }));
	expect(await screen.findByRole('alert')).toBeTruthy();
	expect(screen.getByText('Demo')).toBeTruthy();
});
