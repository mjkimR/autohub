import { cleanup, render, screen, waitFor, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { session } from '$lib/stores/session.svelte';
import SddUnitActions from './SddUnitActions.svelte';
import SddStartOutcome from './SddStartOutcome.svelte';
import { classifyStartFailure, sddStarts } from './sdd-starts.svelte';
const { api } = vi.hoisted(() => ({ api: { POST: vi.fn(), GET: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
const unit = 'docs/proposals/PROP-demo';
const claim = '11111111-2222-4333-8444-555555555555';
beforeEach(() => {
	session.logout();
	api.POST.mockReset();
	api.GET.mockReset().mockResolvedValue({ data: [] });
});
afterEach(cleanup);

function renderPanel() {
	render(SddStartOutcome, {
		state: sddStarts('project'),
		projectId: 'project',
		repository: 'team/app'
	});
	render(SddUnitActions, {
		projectId: 'project',
		repository: 'team/app',
		path: `${unit}/proposal.md`,
		branch: 'main'
	});
}
const refusal = (status: number, detail: string, code?: string) => ({
	error: code ? { detail, code } : { detail },
	response: { status }
});

test('classifies start failures by code and documented claim path', () => {
	const owned = `Activity has unsettled owner claim ${claim}; inspect /api/v1/projects/p/sdd/claims/${claim}`;
	expect(classifyStartFailure(409, 'SDD_ACTIVITY_OWNED', owned)).toEqual({
		outcome: 'retained',
		claimId: claim
	});
	expect(
		classifyStartFailure(409, 'SDD_BRANCH_EXISTS', 'Activity branch has a different owner')
	).toEqual({ outcome: 'refused', claimId: '' });
	expect(
		classifyStartFailure(409, undefined, 'Start request belongs to another activity owner')
	).toEqual({ outcome: 'refused', claimId: '' });
	expect(classifyStartFailure(503, undefined, 'Hub unavailable').outcome).toBe('uncertain');
	expect(classifyStartFailure(undefined, undefined, '').outcome).toBe('uncertain');
});

test('an existing activity branch ends the request beside Start instead of locking the project', async () => {
	api.POST.mockResolvedValue(
		refusal(409, 'Activity branch has a different owner or head', 'SDD_BRANCH_EXISTS')
	);
	renderPanel();
	const user = userEvent.setup();
	await user.click(screen.getByRole('button', { name: 'Start Planning' }));
	const alert = await screen.findByRole('alert');
	expect(alert.textContent).toContain('Planning was not started');
	expect(alert.textContent).toContain('plan-demo');
	expect(
		within(alert)
			.getByRole('link', { name: /Inspect branch on GitHub/ })
			.getAttribute('href')
	).toBe('https://github.com/team/app/tree/plan-demo');
	expect(screen.queryByRole('region', { name: 'Original activity request' })).toBeNull();
	expect(screen.getByRole('button', { name: 'Start Planning' })).toHaveProperty('disabled', false);
	await waitFor(() => expect(document.activeElement?.contains(alert)).toBe(true));
});

test('a configuration refusal routes to the owning project tabs', async () => {
	api.POST.mockResolvedValue(refusal(422, 'Enable the project and connect its GitHub repository'));
	renderPanel();
	await userEvent.setup().click(screen.getByRole('button', { name: 'Start Planning' }));
	const alert = await screen.findByRole('alert');
	expect(alert.textContent).toContain('Enable the project and connect its GitHub repository');
	expect(within(alert).getByRole('link', { name: 'Open Connections' }).getAttribute('href')).toBe(
		'/projects/project?tab=connections'
	);
});

test('a retained owner keeps the exact request and explains the disabled form beside it', async () => {
	api.POST.mockResolvedValue(
		refusal(
			409,
			`Activity has unsettled owner claim ${claim}; inspect /api/v1/projects/project/sdd/claims/${claim}`,
			'SDD_ACTIVITY_OWNED'
		)
	);
	api.GET.mockImplementation(async (path: string) =>
		path.endsWith('/claims/{claim_id}')
			? {
					data: {
						id: claim,
						unit,
						activity: 'plan',
						run_id: 'owner-run',
						settled: false,
						checkpoint_digest: 'digest',
						checkpoint: {}
					}
				}
			: { data: [] }
	);
	renderPanel();
	await userEvent.setup().click(screen.getByRole('button', { name: 'Start Planning' }));
	const card = await screen.findByRole('region', { name: 'Retained activity ownership' });
	expect(await within(card).findByRole('link', { name: 'Open retained Run' })).toBeTruthy();
	expect(within(card).getAllByRole('heading')).toHaveLength(1);
	expect(card.textContent).toContain('is owned by a PR run');
	expect(within(card).getByText('Request details')).toBeTruthy();
	// Claim evidence loads on its own (user decision C).
	await waitFor(() =>
		expect(api.GET).toHaveBeenCalledWith('/api/v1/projects/{project_id}/sdd/claims/{claim_id}', {
			params: { path: { project_id: 'project', claim_id: claim } }
		})
	);
	expect(screen.queryByRole('button', { name: 'Inspect retained owner' })).toBeNull();
	const reason = screen.getByText(/New starts are unavailable while the original Planning request/);
	expect(reason.textContent).toContain(unit);
	expect(screen.getByRole('button', { name: 'Start Planning' })).toHaveProperty('disabled', true);
	expect(screen.getByRole('button', { name: 'Review the original request' })).toBeTruthy();
	// A live PR run owns the activity: dismissing the request ends the project start lock.
	await userEvent.setup().click(within(card).getByRole('button', { name: 'Dismiss request' }));
	await waitFor(() =>
		expect(screen.getByRole('button', { name: 'Start Planning' })).toHaveProperty('disabled', false)
	);
	expect(screen.getByText(/Original request closed/)).toBeTruthy();
});

test('success is confirmed beside Start with the PR run link', async () => {
	api.POST.mockResolvedValue({ data: { id: 'new-run' } });
	renderPanel();
	await userEvent.setup().click(screen.getByRole('button', { name: 'Start Planning' }));
	const link = await screen.findByRole('link', { name: 'Open PR run' });
	expect(link.getAttribute('href')).toBe('/projects/project/runs/new-run');
	expect(screen.getByText(/Planning registered/)).toBeTruthy();
	expect(screen.getAllByRole('link', { name: 'Open PR run' })).toHaveLength(1);
});

test('an active owner of the activity is shown first and demotes Start without blocking it', async () => {
	api.GET.mockResolvedValue({
		data: [
			{
				id: 'plan-run',
				state: 'paused',
				pull_number: 431,
				pull_snapshot: { title: 'Plan' },
				sdd_snapshot: { spec_dir: unit, activity_kind: 'plan' }
			},
			{
				id: 'old-dev',
				state: 'completed',
				pull_number: 400,
				pull_snapshot: { title: 'Old' },
				sdd_snapshot: { spec_dir: unit, activity_kind: 'dev' }
			}
		]
	});
	renderPanel();
	const status = await screen.findByRole('list', { name: 'Unit status' });
	expect(
		within(status)
			.getByRole('link', { name: /Open decisions/ })
			.getAttribute('href')
	).toBe('/projects/project/runs/plan-run#decisions');
	expect(within(status).getByText('Development')).toBeTruthy();
	expect(within(status).queryByRole('link', { name: /Open decisions for PR #400/ })).toBeNull();
	expect(screen.getByText(/PR #431 \(Paused\) already holds Planning for this unit/)).toBeTruthy();
	expect(screen.getByRole('link', { name: 'Open PR #431' })).toBeTruthy();
	expect(screen.getByRole('button', { name: 'Start Planning' })).toHaveProperty('disabled', false);
	const history = screen.getByRole('link', { name: /Old$/ });
	expect(history.getAttribute('href')).toBe('/projects/project/runs/old-dev');
});
