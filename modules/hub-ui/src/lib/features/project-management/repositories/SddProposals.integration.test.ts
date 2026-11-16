import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { session } from '$lib/stores/session.svelte';
import SddUnitActions from './SddUnitActions.svelte';
import SddStartOutcome from './SddStartOutcome.svelte';
import { sddStarts } from './sdd-starts.svelte';
const { api } = vi.hoisted(() => ({ api: { POST: vi.fn(), GET: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
const unit = 'docs/proposals/PROP-demo';
beforeEach(() => {
	session.logout();
	api.POST.mockReset();
	api.GET.mockReset().mockResolvedValue({ data: [] });
});
afterEach(cleanup);

test('reads the selected proposal and reviews explicit activity and base before dispatch', async () => {
	api.POST.mockResolvedValue({ data: { id: 'new-run' } });
	render(SddUnitActions, {
		projectId: 'project',
		repository: 'owner/app',
		path: `${unit}/proposal.md`,
		branch: 'feature'
	});
	const user = userEvent.setup();
	expect(screen.getByLabelText('Activity base branch')).toHaveProperty('value', 'feature');
	await user.selectOptions(screen.getByLabelText('Activity'), 'dev');
	await user.clear(screen.getByLabelText('Activity base branch'));
	await user.type(screen.getByLabelText('Activity base branch'), 'release');
	expect(screen.getByText(/different base from the document branch/)).toBeTruthy();
	await user.click(screen.getByText('Activity preferences'));
	await user.selectOptions(screen.getByLabelText('Proposal activity effort'), 'high');
	await user.click(screen.getByRole('button', { name: 'Start Development' }));
	expect(api.POST).toHaveBeenCalledExactlyOnceWith(
		'/api/v1/projects/{project_id}/sdd/proposals/{slug}/development',
		{
			params: { path: { project_id: 'project', slug: 'demo' } },
			body: { request_id: expect.any(String), base_branch: 'release', activity_effort: 'high' }
		}
	);
	expect(api.GET.mock.calls.some(([path]) => path.endsWith('/proposals'))).toBe(false);
});

test('changing unit or branch resets reviewed intent instead of reusing stale actions', async () => {
	const view = render(SddUnitActions, {
		projectId: 'project',
		repository: 'owner/app',
		path: `${unit}/proposal.md`,
		branch: 'main'
	});
	const user = userEvent.setup();
	await user.clear(screen.getByLabelText('Activity base branch'));
	await user.type(screen.getByLabelText('Activity base branch'), 'old-base');
	await user.selectOptions(screen.getByLabelText('Activity'), 'dev');
	await view.rerender({
		projectId: 'project',
		repository: 'owner/app',
		path: 'docs/proposals/PROP-next/proposal.md',
		branch: 'new-base'
	});
	expect(screen.getByLabelText('Activity base branch')).toHaveProperty('value', 'new-base');
	expect(screen.getByLabelText('Activity')).toHaveProperty('value', 'plan');
});

test('lost start response preserves original intent outside selection and blocks competing enrollment', async () => {
	api.POST.mockRejectedValueOnce(new Error('Lost response')).mockResolvedValueOnce({
		data: { id: 'recovered' }
	});
	const view = render(SddUnitActions, {
		projectId: 'project',
		repository: 'owner/app',
		path: `${unit}/proposal.md`,
		branch: 'feature'
	});
	render(SddStartOutcome, {
		state: sddStarts('project'),
		projectId: 'project',
		repository: 'owner/app'
	});
	const user = userEvent.setup();
	await user.click(screen.getByRole('button', { name: 'Start Planning' }));
	await screen.findByText('Start outcome unresolved');
	await view.rerender({
		projectId: 'project',
		repository: 'owner/app',
		path: 'specs/2026-11/other/spec.md',
		branch: 'main'
	});
	expect(screen.getByRole('region', { name: 'Original activity request' }).textContent).toContain(
		'PROP-demo'
	);
	await user.click(screen.getByText('Enroll an existing PR'));
	await user.type(screen.getByLabelText('Pull request'), '12');
	expect(screen.getByRole('button', { name: 'Enroll PR' })).toHaveProperty('disabled', true);
	await user.click(screen.getByRole('button', { name: 'Retry same request' }));
	await waitFor(() => expect(api.POST).toHaveBeenCalledTimes(2));
	expect(api.POST.mock.calls[1]).toEqual(api.POST.mock.calls[0]);
});
