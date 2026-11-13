import { session } from '$lib/stores/session.svelte';
import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import type { components } from '$lib/api';
import RunDecisionsDialog from './RunDecisionsDialog.svelte';

const { api } = vi.hoisted(() => ({ api: { GET: vi.fn(), POST: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));

const run = {
	id: 'run-1',
	pull_number: 7,
	pull_url: 'https://github.com/owner/app/pull/7',
	pull_snapshot: { title: 'Feature' },
	state: 'blocked',
	revision: 2
} as components['schemas']['PipelineRunRead'];
const question = {
	id: 'question-1',
	question: 'Keep existing behavior?',
	state: 'open',
	actor: 'agent',
	created_at: '2026-09-30T00:00:00Z',
	answers: []
};

beforeEach(() => {
	api.GET.mockReset();
	api.POST.mockReset();
	api.GET.mockImplementation(async (path: string) => ({
		data: path.endsWith('/questions') ? { items: [question], total_count: 1, run_revision: 2 } : run
	}));
});
afterEach(() => {
	session.logout();
	cleanup();
	document.body.innerHTML = '';
	document.body.removeAttribute('style');
});

test('saves an answer separately and explicitly resumes with the new revision', async () => {
	const user = userEvent.setup();
	api.POST.mockImplementation(async () => {
		api.GET.mockImplementation(async (path: string) => ({
			data: path.endsWith('/questions')
				? {
						items: [
							{
								...question,
								state: 'answered',
								answers: [
									{ id: 'answer-1', answer: 'Yes', actor: 'user', created_at: question.created_at }
								]
							}
						],
						total_count: 1,
						run_revision: 3
					}
				: { ...run, revision: 3 }
		}));
		return { data: {} };
	});
	render(RunDecisionsDialog, { run, onclose: vi.fn(), onchange: vi.fn() });
	await screen.findByText('Keep existing behavior?');
	await waitFor(() =>
		expect((screen.getByLabelText('Your answer') as HTMLTextAreaElement).disabled).toBe(false)
	);
	await user.type(await screen.findByLabelText('Your answer'), 'Yes');
	expect((screen.getByLabelText('Your answer') as HTMLTextAreaElement).value).toBe('Yes');
	expect((screen.getByRole('button', { name: 'Save only' }) as HTMLButtonElement).disabled).toBe(
		false
	);
	await user.click(screen.getByRole('button', { name: 'Save only' }));
	await waitFor(() => expect(api.POST).toHaveBeenCalledTimes(1));
	await screen.findByText('Answer saved. The run remains stopped until you resume.');
	expect(api.POST).toHaveBeenCalledTimes(1);
	await user.click(screen.getByRole('button', { name: 'Resume with this answer' }));
	await waitFor(() =>
		expect(api.POST).toHaveBeenLastCalledWith('/api/v1/pipeline-runs/{run_id}/resume', {
			params: { path: { run_id: 'run-1' } },
			body: { request_id: expect.any(String), expected_revision: 3, answer_id: 'answer-1' }
		})
	);
	await screen.findByText('Resume recorded. Agent delivery may still be pending.');
});

function answeredAfterSave(outcome: Record<string, unknown>) {
	api.POST.mockImplementation(async (path: string) => {
		if (path.endsWith('/resume')) return { error: { detail: 'Run changed' } };
		api.GET.mockImplementation(async (getPath: string) => ({
			data: getPath.endsWith('/questions')
				? {
						items: [
							{
								...question,
								state: 'answered',
								answers: [
									{ id: 'answer-1', answer: 'Yes', actor: 'user', created_at: question.created_at }
								]
							}
						],
						total_count: 1,
						run_revision: 3
					}
				: getPath.includes('decision-outcomes')
					? outcome
					: { ...run, revision: 3 }
		}));
		return { data: {} };
	});
}

test('Save and resume saves, then resumes with the saved answer; a refused resume stays recoverable', async () => {
	const user = userEvent.setup();
	answeredAfterSave({
		operation: 'answer',
		request_id: 'x',
		record_state: 'recorded',
		answer_id: 'answer-1',
		run_revision: 3
	});
	render(RunDecisionsDialog, { run, onclose: vi.fn(), onchange: vi.fn() });
	await waitFor(() =>
		expect((screen.getByLabelText('Your answer') as HTMLTextAreaElement).disabled).toBe(false)
	);
	await user.type(screen.getByLabelText('Your answer'), 'Yes');
	await user.click(screen.getByRole('button', { name: 'Save and resume' }));
	await screen.findByText('Answer saved, but the run did not resume.');
	const resume = api.POST.mock.calls.find(([path]) => path.endsWith('/resume'));
	expect(resume?.[1].body).toMatchObject({ expected_revision: 3, answer_id: 'answer-1' });
	expect(api.POST.mock.calls.filter(([path]) => path.endsWith('/answers'))).toHaveLength(1);
	expect(screen.getByRole('button', { name: 'Resume with this answer' })).toBeTruthy();
});

test('retries a lost answer response with the same request identity', async () => {
	const user = userEvent.setup({ delay: null });
	api.POST.mockRejectedValue(new Error('Connection lost'));
	render(RunDecisionsDialog, { run, onclose: vi.fn(), onchange: vi.fn() });
	await screen.findByText('Keep existing behavior?');
	await waitFor(() =>
		expect((screen.getByLabelText('Your answer') as HTMLTextAreaElement).disabled).toBe(false)
	);
	await user.type(await screen.findByLabelText('Your answer'), 'Yes');
	await user.click(screen.getByRole('button', { name: 'Save only' }));
	await screen.findByRole('alert');
	await user.click(screen.getByRole('button', { name: 'Retry same request' }));
	expect(api.POST.mock.calls[1]).toEqual(api.POST.mock.calls[0]);
});

test('keeps the answer request identity after response loss and a revision refresh', async () => {
	const user = userEvent.setup({ delay: null });
	api.POST.mockImplementationOnce(async () => {
		api.GET.mockImplementation(async (path: string) => ({
			data: path.endsWith('/questions')
				? {
						items: [
							{
								...question,
								state: 'answered',
								answers: [
									{ id: 'answer-1', answer: 'Yes', actor: 'user', created_at: question.created_at }
								]
							}
						],
						total_count: 1,
						run_revision: 3
					}
				: { ...run, revision: 3 }
		}));
		throw new Error('Connection lost after commit');
	}).mockResolvedValue({ data: {} });
	render(RunDecisionsDialog, { run, onclose: vi.fn(), onchange: vi.fn() });
	await screen.findByText('Keep existing behavior?');
	await waitFor(() =>
		expect((screen.getByLabelText('Your answer') as HTMLTextAreaElement).disabled).toBe(false)
	);
	await user.type(await screen.findByLabelText('Your answer'), 'Yes');
	await user.click(screen.getByRole('button', { name: 'Save only' }));
	await screen.findByRole('alert');
	const original = api.POST.mock.calls[0][1].body.request_id;
	await user.click(screen.getByRole('button', { name: 'Refresh decisions' }));
	await screen.findByRole('button', { name: 'Resume with this answer' });
	await user.click(screen.getByRole('button', { name: 'Retry same request' }));
	await waitFor(() => expect(api.POST).toHaveBeenCalledTimes(2));
	expect(api.POST.mock.calls[1][1].body).toEqual({
		request_id: original,
		expected_revision: 2,
		answer: 'Yes'
	});
	// A confirmed submission ends the retry identity; a later intentional answer is new.
	await waitFor(() =>
		expect((screen.getByLabelText('Your answer') as HTMLTextAreaElement).disabled).toBe(false)
	);
	await user.type(await screen.findByLabelText('Your answer'), 'Yes');
	await user.click(screen.getByRole('button', { name: 'Save only' }));
	expect(api.POST.mock.calls[2][1].body.request_id).not.toBe(original);
});

test.each(['run-error', 'questions-error', 'revision-mismatch'])(
	'disables controls after %s until a consistent refresh succeeds',
	async (failure) => {
		const user = userEvent.setup();
		api.GET.mockImplementation(async (path: string) => ({
			data: path.endsWith('/questions')
				? { items: [], total_count: 0, run_revision: 2 }
				: { ...run, pause_reason: 'Old stop' }
		}));
		render(RunDecisionsDialog, { run, onclose: vi.fn(), onchange: vi.fn() });
		await screen.findByRole('button', { name: 'Resume after inspection' });
		api.GET.mockImplementation(async (path: string) => {
			if (path.endsWith('/questions'))
				return failure === 'questions-error'
					? { error: { detail: 'Questions unavailable' } }
					: { data: { items: [], total_count: 0, run_revision: 7 } };
			return failure === 'run-error'
				? { error: { detail: 'Current run unavailable' } }
				: {
						data: {
							...run,
							revision: failure === 'revision-mismatch' ? 8 : 7,
							pause_reason: 'New stop'
						}
					};
		});
		await user.click(screen.getByRole('button', { name: 'Refresh decisions' }));
		await screen.findByRole('alert');
		expect(screen.queryByRole('button', { name: 'Resume after inspection' })).toBeNull();
		expect(screen.queryByRole('button', { name: 'Ask and pause' })).toBeNull();
		expect(screen.getByText('Old stop')).toBeTruthy();
		expect(screen.queryByText('New stop')).toBeNull();
		expect(api.POST).not.toHaveBeenCalled();
		api.GET.mockImplementation(async (path: string) => ({
			data: path.endsWith('/questions')
				? { items: [], total_count: 0, run_revision: 8 }
				: { ...run, revision: 8, pause_reason: 'New stop' }
		}));
		api.POST.mockResolvedValue({ data: {} });
		await user.click(screen.getByRole('button', { name: 'Refresh decisions' }));
		await screen.findByText('New stop');
		await user.click(screen.getByRole('button', { name: 'Resume after inspection' }));
		expect(api.POST.mock.calls[0][1].body.expected_revision).toBe(8);
	}
);

test('disables saved-answer resume buttons when refreshing fails', async () => {
	const user = userEvent.setup();
	api.GET.mockImplementation(async (path: string) => ({
		data: path.endsWith('/questions')
			? {
					items: [
						{
							...question,
							state: 'answered',
							answers: [
								{ id: 'answer-1', answer: 'Yes', actor: 'user', created_at: question.created_at }
							]
						}
					],
					total_count: 1,
					run_revision: 2
				}
			: run
	}));
	render(RunDecisionsDialog, { run, onclose: vi.fn(), onchange: vi.fn() });
	await screen.findByRole('button', { name: 'Resume with this answer' });
	api.GET.mockRejectedValue(new Error('Connection lost'));
	await user.click(screen.getByRole('button', { name: 'Refresh decisions' }));
	await screen.findByRole('alert');
	const button = screen.getByRole('button', {
		name: 'Resume with this answer'
	}) as HTMLButtonElement;
	expect(button.disabled).toBe(true);
	await user.click(button);
	expect(api.POST).not.toHaveBeenCalled();
});

test('locks other decision controls until a native approval and refresh finish', async () => {
	const user = userEvent.setup();
	const nativeRun = {
		...run,
		sdd_snapshot: { spec_dir: 'specs/2026-10/feature' },
		sdd_progress: { current: { stage: { human_gate: 'dev-integration', exit: [] } } }
	} as unknown as components['schemas']['PipelineRunRead'];
	api.GET.mockImplementation(async (path: string) => ({
		data: path.endsWith('/questions')
			? { items: [], total_count: 0, run_revision: 2 }
			: path.endsWith('/sdd-decisions')
				? []
				: nativeRun
	}));
	let finish!: () => void;
	api.POST.mockImplementation(
		() =>
			new Promise((resolve) => {
				finish = () => resolve({ data: nativeRun });
			})
	);
	render(RunDecisionsDialog, { run: nativeRun, onclose: vi.fn(), onchange: vi.fn() });
	const approval = screen.getByRole('button', { name: 'Approve integration' }) as HTMLButtonElement;
	await waitFor(() => expect(approval.disabled).toBe(false));
	await user.click(approval);
	expect(
		(screen.getByRole('button', { name: 'Refresh decisions' }) as HTMLButtonElement).disabled
	).toBe(true);
	expect(
		(screen.getByRole('button', { name: 'Request changes' }) as HTMLButtonElement).disabled
	).toBe(true);
	finish();
	await waitFor(() => expect(approval.disabled).toBe(false));
	expect(
		(screen.getByRole('button', { name: 'Refresh decisions' }) as HTMLButtonElement).disabled
	).toBe(false);
});

test('failed inbox inspection leaves every mutation disabled', async () => {
	api.POST.mockResolvedValue({ error: { detail: 'Subject changed' } });
	const selection = {
		key: 'entry',
		fingerprint: 'old',
		subject_id: 'question-1',
		kind: 'run-question'
	} as components['schemas']['DecisionEntryRead'];
	render(RunDecisionsDialog, { run, selection, onclose: vi.fn(), onchange: vi.fn() });
	await screen.findByRole('alert');
	expect(screen.queryByRole('button', { name: 'Save only' })).toBeNull();
	expect(api.GET).not.toHaveBeenCalled();
	expect(api.POST).toHaveBeenCalledWith('/api/v1/pipeline-runs/decisions/review', {
		body: { key: 'entry', fingerprint: 'old' }
	});
});

test('acknowledged inbox dismissal refreshes the list without re-reviewing the removed entry', async () => {
	const user = userEvent.setup();
	let resolved = false;
	const selection = {
		key: 'entry',
		fingerprint: 'fp',
		subject_id: question.id,
		kind: 'run-question'
	} as components['schemas']['DecisionEntryRead'];
	const onchange = vi.fn();
	api.GET.mockImplementation(async (path: string) => ({
		data: path.endsWith('/questions')
			? {
					items: [{ ...question, state: resolved ? 'dismissed' : 'open' }],
					total_count: 1,
					run_revision: 2
				}
			: path.endsWith('/{question_id}')
				? { ...question, state: resolved ? 'dismissed' : 'open' }
				: run
	}));
	api.POST.mockImplementation(async (path: string) => {
		if (path.endsWith('/dismiss')) resolved = true;
		return { data: {} };
	});
	render(RunDecisionsDialog, { run, selection, onclose: vi.fn(), onchange });
	await user.click(await screen.findByText('Dismiss this question'));
	await user.type(screen.getByLabelText('Reason to dismiss'), 'Resolved elsewhere');
	await user.click(screen.getByRole('button', { name: 'Dismiss without resuming' }));
	await waitFor(() => expect(onchange).toHaveBeenCalledOnce());
	expect(api.POST.mock.calls.filter(([path]) => path.endsWith('/decisions/review'))).toHaveLength(
		1
	);
	expect(screen.queryByRole('alert')).toBeNull();
});

test('lost proposal response offers separately reviewed reconciliation after request disappears', async () => {
	const { decisionIntent, decisionBasis } = await import('./decision-intents.svelte');
	const native = {
		...run,
		state: 'blocked' as const,
		sdd_snapshot: { provider: 'devkit-spec', spec_dir: 'docs/proposals/PROP-demo' },
		sdd_progress: { head_sha: 'a'.repeat(40), current: { requests: [] } }
	};
	api.POST.mockRejectedValueOnce(new Error('lost response'));
	await expect(
		decisionIntent(run.id).submit(
			'resume',
			{
				request_id: 'original-proposal',
				expected_revision: run.revision,
				decision: 'accept_plan',
				head_sha: 'a'.repeat(40)
			},
			decisionBasis(native)
		)
	).rejects.toThrow();
	api.GET.mockImplementation(async (path: string) => ({
		data: path.endsWith('/questions')
			? { items: [], total_count: 0, run_revision: run.revision }
			: native
	}));
	api.POST.mockResolvedValue({ data: native });
	render(RunDecisionsDialog, { run: native, onclose: vi.fn(), onchange: vi.fn() });
	const user = userEvent.setup();
	await user.click(
		await screen.findByRole('button', { name: 'Review publication reconciliation' })
	);
	await user.click(
		await screen.findByRole('button', { name: 'Confirm publication reconciliation' })
	);
	await waitFor(() => expect(api.POST).toHaveBeenCalledTimes(2));
	const recoveryBody = api.POST.mock.calls[1][1].body;
	expect(recoveryBody.request_id).not.toBe('original-proposal');
	expect(recoveryBody.expected_revision).toBe(run.revision);
	expect(recoveryBody.decision).toBeUndefined();
	expect(decisionIntent(run.id).intent?.requestId).toBe('original-proposal');
});

test('retains last successful observation time after a failed refresh', async () => {
	render(RunDecisionsDialog, { run, onclose: vi.fn(), onchange: vi.fn() });
	const observed = await screen.findByText(/Last loaded:/);
	const prior = observed.textContent;
	api.GET.mockRejectedValueOnce(new Error('refresh unavailable'));
	await userEvent.setup().click(screen.getByRole('button', { name: 'Refresh decisions' }));
	await screen.findByRole('alert');
	expect(screen.getByText(/Last loaded:/).textContent).toBe(prior);
});
