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
	await user.type(screen.getByLabelText('Your answer'), 'Yes');
	await user.click(screen.getByRole('button', { name: 'Save answer' }));
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

test('retries a lost answer response with the same request identity', async () => {
	const user = userEvent.setup({ delay: null });
	api.POST.mockRejectedValue(new Error('Connection lost'));
	render(RunDecisionsDialog, { run, onclose: vi.fn(), onchange: vi.fn() });
	await screen.findByText('Keep existing behavior?');
	await user.type(screen.getByLabelText('Your answer'), 'Yes');
	await user.click(screen.getByRole('button', { name: 'Save answer' }));
	await screen.findByRole('alert');
	await user.click(screen.getByRole('button', { name: 'Save answer' }));
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
	await user.type(screen.getByLabelText('Your answer'), 'Yes');
	await user.click(screen.getByRole('button', { name: 'Save answer' }));
	await screen.findByRole('alert');
	const original = api.POST.mock.calls[0][1].body.request_id;
	await user.click(screen.getByRole('button', { name: 'Refresh decisions' }));
	await screen.findByRole('button', { name: 'Resume with this answer' });
	await user.click(screen.getByRole('button', { name: 'Save answer' }));
	await screen.findByText('Answer saved. The run remains stopped until you resume.');
	expect(api.POST.mock.calls[1][1].body).toEqual({
		request_id: original,
		expected_revision: 3,
		answer: 'Yes'
	});
	// A confirmed submission ends the retry identity; a later intentional answer is new.
	await user.type(screen.getByLabelText('Your answer'), 'Yes');
	await user.click(screen.getByRole('button', { name: 'Save answer' }));
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
