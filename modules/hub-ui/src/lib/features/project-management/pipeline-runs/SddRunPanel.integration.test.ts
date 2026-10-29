import { cleanup, render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import type { components } from '$lib/api';
import SddRunPanel from './SddRunPanel.svelte';
import SddDecisionHistory from './SddDecisionHistory.svelte';

const { api } = vi.hoisted(() => ({ api: { POST: vi.fn(), GET: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
const run = {
	id: 'run-1',
	revision: 3,
	state: 'paused',
	pull_url: 'https://github.com/owner/app/pull/7',
	sdd_snapshot: { spec_dir: 'specs/2026-10/20261010-feature' },
	sdd_progress: {
		head_sha: 'a'.repeat(40),
		base_sha: 'b'.repeat(40),
		current: {
			stage: { name: 'Integration approval', human_gate: 'dev-integration', exit: [] },
			done: ['review']
		}
	}
} as unknown as components['schemas']['PipelineRunRead'];
beforeEach(() => {
	api.POST.mockReset();
	api.GET.mockReset().mockResolvedValue({ data: [] });
});
afterEach(cleanup);

test('withheld automatic Planning requires an explicit proposal approval', async () => {
	const user = userEvent.setup();
	const onchange = vi.fn();
	api.POST.mockResolvedValue({ data: run });
	render(SddRunPanel, {
		run: {
			...run,
			sdd_snapshot: { provider: 'devkit-spec', spec_dir: 'docs/proposals/PROP-demo' },
			sdd_progress: {
				...run.sdd_progress,
				current: { complete: true, stage: null, requests: [] },
				approval_withheld: true,
				waiting_for_plan_approval: true
			}
		},
		onchange
	});
	expect(screen.getByText('Review & approve proposal')).toBeTruthy();
	expect(api.POST).not.toHaveBeenCalled();
	await user.click(screen.getByRole('button', { name: 'Approve proposal' }));
	expect(api.POST.mock.calls[0][1].body).toMatchObject({
		decision: 'approve',
		expected_revision: run.revision
	});
	expect(onchange).toHaveBeenCalledOnce();
});

test('Planning evidence precedes approval and preserves effort, support rounds, findings and gaps', () => {
	render(SddRunPanel, {
		run: {
			...run,
			sdd_snapshot: { spec_dir: 'docs/proposals/PROP-demo', provider: 'devkit-spec' },
			sdd_progress: {
				...run.sdd_progress,
				proposal: { planning_effort: 'medium', dev_effort: 'high' },
				current: {
					requests: [
						{
							id: 'gate:plan-accept',
							kind: 'approve',
							title: 'Direction',
							answer: 'record',
							options: []
						}
					]
				},
				review_gaps: ['worker-01.yaml: high effort has no scout record in this workflow segment'],
				reports: [
					{
						kind: 'worker',
						file: 'envelopes/worker-01.yaml',
						status: 'completed',
						activity_effort: 'high',
						workflow: 'sdd-proposal',
						segment: 0,
						summary: 'Design settled',
						assumptions: ['API remains stable']
					},
					{
						kind: 'challenger',
						file: 'envelopes/challenger-01.yaml',
						status: 'completed',
						summary: 'Reviewed alternatives',
						findings: [
							{
								issue: 'Boundary unclear',
								severity: 'P2',
								resolution: 'open',
								evidence: '<script>text</script>'
							}
						]
					},
					{
						kind: 'reverify',
						file: 'envelopes/reverify-01.yaml',
						status: 'completed',
						review: 'challenger-01.yaml',
						summary: 'Boundary resolved'
					},
					{
						kind: 'ux-review',
						file: 'envelopes/ux-review-01.yaml',
						status: 'completed',
						stage: 'spike',
						summary: 'Screens walked through',
						findings: [{ issue: 'Empty state unclear', resolution: 'open', evidence: 'Screen 2' }]
					}
				]
			}
		},
		onchange: vi.fn()
	});
	const evidence = screen.getByRole('region', { name: 'Planning decision evidence' });
	expect(evidence.textContent).toContain('Planning medium');
	expect(evidence.textContent).toContain('Development high');
	expect(evidence.textContent).toContain('effort high');
	expect(evidence.textContent).toContain('Closes round: challenger-01.yaml');
	expect(evidence.textContent).toContain('UX review');
	expect(evidence.textContent).toContain('Screens walked through');
	expect(screen.getByText(/high effort has no scout/)).toBeTruthy();
	expect(screen.getByText('evidence: <script>text</script>')).toBeTruthy();
	expect(evidence.querySelector('script')).toBeNull();
	expect(
		evidence.compareDocumentPosition(screen.getByRole('button', { name: 'Accept proposal' })) &
			Node.DOCUMENT_POSITION_FOLLOWING
	).toBeTruthy();
});

test('uncertain publication retries the saved request identity and refreshes the run', async () => {
	const user = userEvent.setup();
	const saved = {
		request_id: 'saved-id',
		expected_revision: 3,
		decision: 'accept_plan',
		head_sha: 'a'.repeat(40),
		feedback: 'Go'
	};
	api.GET.mockResolvedValue({
		data: [
			{ id: 'saved-id', action: 'accept_plan', publication: { state: 'uncertain' }, request: saved }
		]
	});
	api.POST.mockResolvedValue({ data: run });
	const onchange = vi.fn();
	render(SddDecisionHistory, { runId: run.id, revision: 3, onchange });
	await user.click(await screen.findByRole('button', { name: 'Reconcile decision' }));
	expect(api.POST.mock.calls[0][1].body).toEqual(saved);
	expect(onchange).toHaveBeenCalledOnce();
});

test('approval binds the inspected run revision and reuses identity after a lost response', async () => {
	const user = userEvent.setup({ delay: null });
	api.POST.mockRejectedValueOnce(new Error('Connection lost')).mockResolvedValueOnce({
		data: { ...run, state: 'dispatching' }
	});
	render(SddRunPanel, { run, onchange: vi.fn() });
	await user.click(screen.getByRole('button', { name: 'Approve integration' }));
	const first = api.POST.mock.calls[0][1].body;
	expect(first).toMatchObject({ expected_revision: 3, decision: 'approve' });
	await screen.findByRole('alert');
	await user.click(screen.getByRole('button', { name: 'Approve integration' }));
	expect(api.POST.mock.calls[1][1].body.request_id).toBe(first.request_id);
	expect(screen.getByRole('link').getAttribute('href')).toContain(`/tree/${'a'.repeat(40)}/specs/`);
});

test('rework sends feedback separately from approval', async () => {
	const user = userEvent.setup();
	const onchange = vi.fn();
	api.POST.mockResolvedValue({ data: { ...run, state: 'dispatching' } });
	render(SddRunPanel, { run, onchange });
	expect(screen.queryByRole('textbox')).toBeNull();
	await user.click(screen.getByRole('button', { name: 'Request changes' }));
	await user.type(screen.getByLabelText('Requested changes'), 'Keep the API');
	await user.click(screen.getByRole('button', { name: 'Send change request' }));
	expect(api.POST.mock.calls[0][1].body).toMatchObject({
		decision: 'revise',
		feedback: 'Keep the API'
	});
	expect(onchange).toHaveBeenCalledOnce();
});

test('shows approval history and prevents decisions when parent evidence is unavailable', async () => {
	api.GET.mockResolvedValue({
		data: [
			{ action: 'revoke', actor: 'user:operator', feedback: 'Recheck scope', head_sha: 'old-head' }
		]
	});
	render(SddRunPanel, { run, onchange: vi.fn(), disabled: true });
	render(SddDecisionHistory, { runId: run.id, revision: run.revision });
	expect(
		(screen.getByRole('button', { name: 'Approve integration' }) as HTMLButtonElement).disabled
	).toBe(true);
	expect(await screen.findByText('Recheck scope')).toBeTruthy();
});

test('canceling a change request does not attach abandoned feedback to approval', async () => {
	const user = userEvent.setup();
	api.POST.mockResolvedValue({ data: run });
	render(SddRunPanel, { run, onchange: vi.fn() });
	await user.click(screen.getByRole('button', { name: 'Request changes' }));
	await user.type(screen.getByLabelText('Requested changes'), 'Abandoned change');
	await user.click(screen.getByRole('button', { name: 'Cancel' }));
	expect(api.POST).not.toHaveBeenCalled();
	await user.click(screen.getByRole('button', { name: 'Approve integration' }));
	expect(api.POST.mock.calls[0][1].body).toMatchObject({ decision: 'approve', feedback: '' });
});

test('pending questions disable integration actions and explain the next step', () => {
	render(SddRunPanel, { run, onchange: vi.fn(), questionPending: true });
	expect(
		(screen.getByRole('button', { name: 'Approve integration' }) as HTMLButtonElement).disabled
	).toBe(true);
	expect(screen.getByText(/Answer or dismiss the pending question above/)).toBeTruthy();
});

test('history can recover from a read failure without changing the run revision', async () => {
	const user = userEvent.setup();
	api.GET.mockRejectedValueOnce(new Error('Connection lost')).mockResolvedValueOnce({ data: [] });
	render(SddDecisionHistory, { runId: run.id, revision: run.revision });
	await screen.findByText(/Connection lost/);
	await user.click(screen.getByRole('button', { name: 'Refresh approval history' }));
	expect(await screen.findByText(/No decisions yet/)).toBeTruthy();
});

test('shows report evidence at the inspected commit and treats repository text as text', () => {
	render(SddRunPanel, {
		run: {
			...run,
			sdd_progress: {
				...run.sdd_progress,
				reports: [
					{
						kind: 'final-report',
						file: 'envelopes/final-report-01.yaml',
						status: 'completed',
						summary: '<script>unsafe()</script> Verified delivery',
						checks: { tests: 'PASS 42 tests' }
					}
				],
				lint_diagnostic: 'Sdd lint failed (RULE_VIOLATIONS_DETECTED). Fix the reported rules.'
			}
		},
		onchange: vi.fn()
	});
	expect(screen.getByText('<script>unsafe()</script> Verified delivery')).toBeTruthy();
	expect(screen.getByText('PASS 42 tests')).toBeTruthy();
	expect(
		screen.getByRole('link', { name: 'Read full evidence at this commit' }).getAttribute('href')
	).toBe(
		`https://github.com/owner/app/tree/${'a'.repeat(40)}/specs/2026-10/20261010-feature/envelopes/final-report-01.yaml`
	);
	expect(screen.getByText(/Sdd lint failed/)).toBeTruthy();
});

test('shows best-effort runtime warnings from the inspected evidence as text', () => {
	render(SddRunPanel, {
		run: {
			...run,
			sdd_progress: {
				...run.sdd_progress,
				warnings: [
					{ code: 'RECEIPT_STALE', detail: '<b>Receipt</b> differs from the reviewed runtime' }
				]
			}
		},
		onchange: vi.fn()
	});
	expect(screen.getByText('<b>Receipt</b> differs from the reviewed runtime')).toBeTruthy();
	expect(screen.getByRole('button', { name: 'Approve integration' })).toBeTruthy();
});
