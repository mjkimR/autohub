import { cleanup, render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import type { components } from '$lib/api';
import DecisionQuestion from './DecisionQuestion.svelte';

const question = {
	id: 'q1',
	pipeline_run_id: 'run-1',
	execution_attempt_id: null,
	head_sha: 'a'.repeat(40),
	question: 'Which API version?',
	actor: 'agent',
	source: 'agent',
	state: 'open',
	resolution: null,
	created_at: '2026-11-12T09:00:00Z',
	answers: []
} as unknown as components['schemas']['QuestionRead'];
afterEach(cleanup);

function setup(onsave = vi.fn(), onresume = vi.fn()) {
	render(DecisionQuestion, { question, actionable: true, onsave, onresume });
	return { user: userEvent.setup(), onsave, onresume };
}
async function type(user: ReturnType<typeof userEvent.setup>, text = 'Use v2') {
	await user.type(screen.getByLabelText('Your answer'), text);
}

test('without onsave the question renders no answer composer (backward compatible)', () => {
	render(DecisionQuestion, { question, actionable: true, onresume: vi.fn() });
	expect(screen.queryByRole('button', { name: 'Save and resume' })).toBeNull();
	expect(screen.queryByLabelText('Your answer')).toBeNull();
});

test('Save only saves the answer and never resumes', async () => {
	const { user, onsave, onresume } = setup(vi.fn().mockResolvedValue('a1'));
	await type(user);
	await user.click(screen.getByRole('button', { name: 'Save only' }));
	expect(onsave).toHaveBeenCalledWith('Use v2');
	expect(onresume).not.toHaveBeenCalled();
	expect((screen.getByLabelText('Your answer') as HTMLTextAreaElement).value).toBe('');
});

test('Save and resume saves first, then resumes with exactly that saved answer', async () => {
	const order: string[] = [];
	const onsave = vi.fn(async () => {
		order.push('save');
		return 'a1';
	});
	const onresume = vi.fn(async (id: string) => {
		order.push(`resume:${id}`);
	});
	const { user } = setup(onsave, onresume);
	await type(user);
	await user.click(screen.getByRole('button', { name: 'Save and resume' }));
	expect(order).toEqual(['save', 'resume:a1']);
	expect(screen.queryByRole('alert')).toBeNull();
});

test('a failed resume keeps the save and points to the saved answer instead of re-saving', async () => {
	const onresume = vi.fn().mockRejectedValue(new Error('Run changed'));
	const { user, onsave } = setup(vi.fn().mockResolvedValue('a1'), onresume);
	await type(user);
	await user.click(screen.getByRole('button', { name: 'Save and resume' }));
	const alert = await screen.findByRole('alert');
	expect(alert.textContent).toContain('Answer saved, but the run did not resume.');
	expect(alert.textContent).toContain('Run changed');
	expect(alert.textContent).toContain('choose Resume with this answer');
	expect(onsave).toHaveBeenCalledOnce();
	expect(onresume).toHaveBeenCalledWith('a1');
	expect((screen.getByLabelText('Your answer') as HTMLTextAreaElement).value).toBe('');
});

test('an unconfirmed save keeps the text and does not resume', async () => {
	const { user, onresume } = setup(vi.fn().mockRejectedValue(new Error('Outcome unknown')));
	await type(user);
	await user.click(screen.getByRole('button', { name: 'Save and resume' }));
	expect((await screen.findByRole('alert')).textContent).toContain('Answer not saved.');
	expect(onresume).not.toHaveBeenCalled();
	expect((screen.getByLabelText('Your answer') as HTMLTextAreaElement).value).toBe('Use v2');
});

test('a save without an identified answer asks for explicit selection instead of resuming', async () => {
	const { user, onresume } = setup(vi.fn().mockResolvedValue(undefined));
	await type(user);
	await user.click(screen.getByRole('button', { name: 'Save and resume' }));
	const alert = await screen.findByRole('alert');
	expect(alert.textContent).toContain('no resume was sent');
	expect(onresume).not.toHaveBeenCalled();
});

test('a refused explicit resume is shown beside its saved answer', async () => {
	const user = userEvent.setup();
	const onresume = vi.fn().mockRejectedValue(new Error('PR changed since the question'));
	render(DecisionQuestion, {
		question: {
			...question,
			state: 'answered',
			answers: [
				{ id: 'a1', answer: 'Use v2', actor: 'me', created_at: question.created_at }
			] as components['schemas']['QuestionRead']['answers']
		},
		actionable: true,
		onresume
	});
	await user.click(screen.getByRole('button', { name: 'Resume with this answer' }));
	expect(onresume).toHaveBeenCalledWith('a1');
	expect((await screen.findByRole('alert')).textContent).toContain('PR changed since the question');
});

test('with an unapplied saved answer, its resume stays primary and a new answer is collapsed', () => {
	render(DecisionQuestion, {
		question: {
			...question,
			state: 'answered',
			answers: [
				{ id: 'a1', answer: 'Use v2', actor: 'me', created_at: question.created_at }
			] as components['schemas']['QuestionRead']['answers']
		},
		actionable: true,
		onresume: vi.fn(),
		onsave: vi.fn()
	});
	expect(screen.getByRole('button', { name: 'Resume with this answer' })).toBeTruthy();
	const other = screen.getByText('Answer differently').closest('details')!;
	expect(other.open).toBe(false);
	expect(other.contains(screen.getByRole('button', { name: 'Save and resume' }))).toBe(true);
});
