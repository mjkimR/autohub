import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import SddExecution from './SddExecution.svelte';

const { api } = vi.hoisted(() => ({ api: { POST: vi.fn(), GET: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
beforeEach(() => {
	api.POST.mockReset();
	api.GET.mockReset().mockResolvedValue({ data: [] });
});
afterEach(cleanup);

test('readiness shows best-effort warnings without blocking the start', async () => {
	const user = userEvent.setup();
	api.POST.mockResolvedValueOnce({
		data: {
			ready: true,
			head_sha: 'a'.repeat(40),
			cli_version: 'devkit-spec:lock',
			warnings: [{ code: 'RECEIPT_STALE', detail: 'Receipt differs from the reviewed runtime' }]
		}
	});
	render(SddExecution, { projectId: 'project', selectedSpec: 'specs/2026-10/20261010-feature' });
	await user.click(screen.getByRole('button', { name: 'Check readiness' }));
	expect(await screen.findByText(/Inspected commit aaaaaaaaaaaa/)).toBeTruthy();
	expect(screen.getByText('Receipt differs from the reviewed runtime')).toBeTruthy();
	expect(
		(screen.getByRole('button', { name: 'Start execution' }) as HTMLButtonElement).disabled
	).toBe(false);
});

test('a failed inspection replaces earlier warnings with its reason', async () => {
	const user = userEvent.setup();
	api.POST.mockResolvedValueOnce({
		data: {
			ready: true,
			head_sha: 'a'.repeat(40),
			cli_version: 'devkit-spec:lock',
			warnings: [{ code: 'RUNTIME_REVISION_MISMATCH', detail: 'Repository locks another revision' }]
		}
	}).mockResolvedValueOnce({ data: { ready: false, reason: 'Select an open pull request' } });
	render(SddExecution, { projectId: 'project', selectedSpec: 'specs/2026-10/20261010-feature' });
	await user.click(screen.getByRole('button', { name: 'Check readiness' }));
	expect(await screen.findByText('Repository locks another revision')).toBeTruthy();
	await user.click(screen.getByRole('button', { name: 'Check readiness' }));
	expect(await screen.findByRole('alert')).toBeTruthy();
	expect(screen.queryByText('Repository locks another revision')).toBeNull();
	expect(
		(screen.getByRole('button', { name: 'Start execution' }) as HTMLButtonElement).disabled
	).toBe(true);
});

test('start sends the chosen activity effort and the runtime check reports the host', async () => {
	const user = userEvent.setup();
	api.GET.mockImplementation(async (path: string) =>
		path.endsWith('/sdd/runtime')
			? {
					data: { ok: true, isolation: 'bubblewrap', revisions: { 'devkit-spec': 'f'.repeat(40) } }
				}
			: { data: [] }
	);
	api.POST.mockImplementation(async (path: string) =>
		path.endsWith('/sdd/readiness')
			? {
					data: {
						ready: true,
						head_sha: 'a'.repeat(40),
						cli_version: 'devkit-spec:lock',
						warnings: []
					}
				}
			: { data: { id: 'run-1' } }
	);
	render(SddExecution, { projectId: 'project', selectedSpec: 'specs/2026-10/20261010-feature' });
	await user.click(screen.getByRole('button', { name: 'Check runtime' }));
	expect(await screen.findByText(/Runtime bubblewrap: ok · devkit-spec ffffffffffff/)).toBeTruthy();
	await user.selectOptions(screen.getByLabelText('Activity effort'), 'high');
	await user.click(screen.getByRole('button', { name: 'Check readiness' }));
	await screen.findByText(/Inspected commit/);
	await user.click(screen.getByRole('button', { name: 'Start execution' }));
	const start = api.POST.mock.calls.find((call) => String(call[0]).endsWith('/runs'));
	expect(start?.[1].body).toMatchObject({ activity_effort: 'high', implemented: false });
});

test('an unavailable runtime is reported as an error with its detail', async () => {
	const user = userEvent.setup();
	api.GET.mockResolvedValue({
		data: {
			ok: false,
			isolation: null,
			detail: 'Provision the locked runtime with just install-sdd'
		}
	});
	render(SddExecution, { projectId: 'project' });
	await user.click(screen.getByRole('button', { name: 'Check runtime' }));
	expect(await screen.findByRole('alert')).toBeTruthy();
	expect(screen.getByText(/Runtime without a sandbox: unavailable/)).toBeTruthy();
});

test('eligible registration previews waits and policy without answering them', async () => {
	const user = userEvent.setup();
	api.POST.mockResolvedValueOnce({
		data: {
			ready: true,
			head_sha: 'a'.repeat(40),
			cli_version: 'devkit-spec:lock',
			current: {
				stage: { id: 'review', name: 'Review the plan', human_gate: 'plan-accept' },
				blocked: true,
				problems: [{ cause: 'The test fixture needs repair' }],
				pending_questions: [{ id: 'choice', title: 'Which provider should be used?' }],
				requests: [{ id: 'gate:plan-accept', kind: 'approve', title: 'Accept direction' }]
			},
			policy: { approvals: { 'plan-accept': { policy: 'ask', source: 'default' } } }
		}
	});
	render(SddExecution, { projectId: 'project', selectedSpec: 'specs/2026-10/20261010-feature' });
	await user.click(screen.getByRole('button', { name: 'Check readiness' }));
	const preview = await screen.findByRole('region', { name: 'Execution preview' });
	expect(preview.textContent).toContain('Eligible to register');
	expect(preview.textContent).toContain('Review the plan');
	expect(preview.textContent).toContain('Workflow input reported');
	expect(preview.textContent).toContain('The test fixture needs repair');
	expect(preview.textContent).toContain('Which provider should be used?');
	expect(preview.textContent).toMatch(/Approval requested:\s+Accept direction/);
	expect(preview.textContent).toContain('Explicit approval required');
	expect(preview.querySelector('button')).toBeNull();
	expect(api.POST).toHaveBeenCalledTimes(1);
	expect(
		(screen.getByRole('button', { name: 'Start execution' }) as HTMLButtonElement).disabled
	).toBe(false);
});

test('automatic policy is separate from an active approval wait', async () => {
	const user = userEvent.setup();
	api.POST.mockResolvedValueOnce({
		data: {
			ready: true,
			head_sha: 'a'.repeat(40),
			current: { stage: { name: 'Final checks', human_gate: 'dev-integration' }, requests: [] },
			policy: { approvals: { 'dev-integration': { policy: 'auto', source: 'config' } } }
		}
	});
	render(SddExecution, { projectId: 'project', selectedSpec: 'specs/2026-10/20261010-feature' });
	await user.click(screen.getByRole('button', { name: 'Check readiness' }));
	expect(await screen.findByText('No workflow input is currently waiting.')).toBeTruthy();
	expect(screen.getByText(/Delegated by policy/)).toBeTruthy();
	expect(screen.queryByText('Workflow input reported')).toBeNull();
});

test('failed readiness keeps structured diagnostics visible and prevents registration', async () => {
	const user = userEvent.setup();
	api.POST.mockResolvedValueOnce({
		data: {
			ready: false,
			reason: 'Runtime unavailable',
			diagnostics: [
				{
					code: 'COMMAND_FAILED',
					severity: 'error',
					category: 'runtime',
					message: 'The reviewed runtime could not evaluate this repository.',
					action: 'Ask the runtime operator to inspect the installation.',
					retry: 'after_fix',
					target_files: []
				}
			]
		}
	});
	render(SddExecution, { projectId: 'project', selectedSpec: 'specs/2026-10/20261010-feature' });
	await user.click(screen.getByRole('button', { name: 'Check readiness' }));
	expect(await screen.findByText('COMMAND_FAILED')).toBeTruthy();
	expect(screen.getByText('Runtime setup')).toBeTruthy();
	expect(screen.getByText(/Ask the runtime operator/)).toBeTruthy();
	expect(screen.getByText('Reinspect after repair.')).toBeTruthy();
	expect(screen.queryByRole('region', { name: 'Execution preview' })).toBeNull();
	expect(
		(screen.getByRole('button', { name: 'Start execution' }) as HTMLButtonElement).disabled
	).toBe(true);
});

test('changing the selected unit hides its earlier preview and requires a new inspection', async () => {
	const user = userEvent.setup();
	api.POST.mockResolvedValueOnce({
		data: { ready: true, head_sha: 'a'.repeat(40), current: { stage: { name: 'Old stage' } } }
	});
	const view = render(SddExecution, {
		projectId: 'project',
		selectedSpec: 'specs/2026-10/20261010-feature'
	});
	await user.click(screen.getByRole('button', { name: 'Check readiness' }));
	expect(await screen.findByText('Old stage')).toBeTruthy();
	await view.rerender({ projectId: 'project', selectedSpec: 'specs/2026-10/20261010-other' });
	expect(screen.queryByText('Old stage')).toBeNull();
	expect(
		(screen.getByRole('button', { name: 'Start execution' }) as HTMLButtonElement).disabled
	).toBe(true);
});

test.each(['success', 'refusal', 'error'])(
	'late %s inspection for another PR is discarded',
	async (outcome) => {
		const user = userEvent.setup();
		let finish!: (result: unknown) => void;
		api.POST.mockReturnValueOnce(
			new Promise((resolve) => {
				finish = resolve;
			})
		);
		const view = render(SddExecution, {
			projectId: 'old-project',
			selectedSpec: 'specs/2026-10/20261010-feature'
		});
		await user.click(screen.getByRole('button', { name: 'Check readiness' }));
		await view.rerender({ projectId: 'new-project', selectedSpec: 'specs/2026-10/20261010-other' });
		finish(
			outcome === 'success'
				? {
						data: {
							ready: true,
							head_sha: 'a'.repeat(40),
							current: { stage: { name: 'Old stage' } }
						}
					}
				: outcome === 'refusal'
					? { data: { ready: false, reason: 'Old refusal' } }
					: { error: { detail: 'Old error' } }
		);
		await waitFor(() =>
			expect(
				(screen.getByRole('button', { name: 'Check readiness' }) as HTMLButtonElement).disabled
			).toBe(false)
		);
		expect(screen.queryByText('Old stage')).toBeNull();
		expect(screen.queryByText('Old refusal')).toBeNull();
		expect(screen.queryByText('Old error')).toBeNull();
		expect(
			(screen.getByRole('button', { name: 'Start execution' }) as HTMLButtonElement).disabled
		).toBe(true);
	}
);
