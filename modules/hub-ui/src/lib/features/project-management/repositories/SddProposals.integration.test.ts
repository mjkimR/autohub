import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { session } from '$lib/stores/session.svelte';
import SddProposals from './SddProposals.svelte';
import SddExecution from './SddExecution.svelte';

const { api } = vi.hoisted(() => ({ api: { POST: vi.fn(), GET: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
const proposal = {
	slug: 'demo',
	id: 'PROP-demo',
	path: 'docs/proposals/PROP-demo',
	title: 'Demo',
	status: 'rejected',
	display_status: 'rejected',
	task_kind: 'feature',
	plan_branch: false,
	dev_branch: false,
	plan_pull: null,
	dev_pull: null,
	run: null,
	actions: [],
	note: null
};
beforeEach(() => {
	session.logout();
	api.POST.mockReset();
	api.GET.mockReset().mockImplementation(async (path: string) => ({
		data: path.endsWith('/proposals')
			? { base_branch: 'main', base_sha: 'b'.repeat(40), items: [proposal], truncated: false }
			: []
	}));
});
afterEach(cleanup);

test('offers explicit Planning and Development intents independently of descriptive status', async () => {
	api.POST.mockResolvedValue({ data: { id: 'new-run' } });
	render(SddProposals, { projectId: 'project', repository: 'owner/app' });
	const user = userEvent.setup();
	await user.click(await screen.findByRole('button', { name: 'Start Planning' }));
	await screen.findByRole('link', { name: 'Open PR run' });
	expect(api.POST.mock.calls[0][0]).toBe(
		'/api/v1/projects/{project_id}/sdd/proposals/{slug}/planning'
	);
	expect(api.POST.mock.calls[0][1].body).toMatchObject({
		request_id: expect.any(String),
		base_branch: 'main'
	});
	await user.selectOptions(screen.getByLabelText('Proposal activity effort'), 'high');
	await user.click(screen.getByRole('button', { name: 'Start Development' }));
	expect(api.POST.mock.calls[1][0]).toBe(
		'/api/v1/projects/{project_id}/sdd/proposals/{slug}/development'
	);
	expect(api.POST.mock.calls[1][1].body.activity_effort).toBe('high');
	expect(screen.queryByRole('button', { name: /Reject|Accept|Review & accept/ })).toBeNull();
});

test('lost start response preserves intent and blocks competing enrollment until same-request recovery', async () => {
	api.POST.mockRejectedValueOnce(new Error('Lost response')).mockResolvedValueOnce({
		data: { id: 'recovered' }
	});
	render(SddProposals, { projectId: 'project', repository: 'owner/app' });
	render(SddExecution, { projectId: 'project', selectedSpec: 'specs/2026-11/other' });
	const user = userEvent.setup();
	await user.click(await screen.findByRole('button', { name: 'Start Planning' }));
	await screen.findByText('Start outcome unresolved');
	expect(screen.getByRole('region', { name: 'Original activity request' }).textContent).toContain(
		'PROP-demo'
	);
	expect(
		(screen.getByRole('button', { name: 'Start Development' }) as HTMLButtonElement).disabled
	).toBe(true);
	expect(
		(screen.getByRole('button', { name: 'Start execution' }) as HTMLButtonElement).disabled
	).toBe(true);
	await user.click(screen.getByRole('button', { name: 'Retry same request' }));
	await waitFor(() => expect(api.POST).toHaveBeenCalledTimes(2));
	expect(api.POST.mock.calls[1]).toEqual(api.POST.mock.calls[0]);
});
