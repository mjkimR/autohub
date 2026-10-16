import { cleanup, render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, test, vi } from 'vitest';
import type { components } from '$lib/api';
import SddWorkflowRequests from './SddWorkflowRequests.svelte';

const { api } = vi.hoisted(() => ({ api: { POST: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
afterEach(() => {
	cleanup();
	api.POST.mockReset();
});
const run = {
	id: 'run',
	revision: 5,
	state: 'blocked',
	sdd_progress: {
		current: {
			requests: [
				{
					id: 'handoff',
					kind: 'choose',
					title: 'Choose workflow',
					prompt: 'Choose the delivery route',
					options: [
						{ id: 'direct', description: 'Ready for delivery', eligible: true, recommended: true },
						{
							id: 'incubated',
							description: 'Proposal missing',
							eligible: false,
							recommended: false
						}
					]
				}
			]
		}
	}
} as unknown as components['schemas']['PipelineRunRead'];

test('only eligible choices can be accepted and retries preserve the receipt identity', async () => {
	const user = userEvent.setup({ delay: null });
	api.POST.mockRejectedValueOnce(new Error('Connection lost')).mockResolvedValueOnce({ data: run });
	render(SddWorkflowRequests, { run, onchange: vi.fn() });
	const confirm = screen.getByRole('button', { name: 'Confirm choice' }) as HTMLButtonElement;
	expect(confirm.disabled).toBe(true);
	expect((screen.getByRole('radio', { name: /incubated/ }) as HTMLInputElement).disabled).toBe(
		true
	);
	await user.click(screen.getByRole('radio', { name: /direct/ }));
	await user.click(confirm);
	await screen.findByRole('alert');
	const first = api.POST.mock.calls[0][1].body;
	expect(first).toMatchObject({
		expected_revision: 5,
		workflow_answer: { request: 'handoff', action: 'accept', value: 'direct' }
	});
	await user.click(confirm);
	expect(api.POST.mock.calls[1][1].body.request_id).toBe(first.request_id);
});

test('deferral records cancel without integration revocation or a selected option', async () => {
	api.POST.mockResolvedValue({ data: run });
	render(SddWorkflowRequests, { run, onchange: vi.fn() });
	await userEvent
		.setup({ delay: null })
		.click(screen.getByRole('button', { name: 'Defer decision' }));
	expect(api.POST.mock.calls[0][1].body).toMatchObject({
		workflow_answer: { request: 'handoff', action: 'cancel', value: null }
	});
	expect(api.POST.mock.calls[0][1].body.decision).toBeUndefined();
});

const questionRun = {
	...run,
	sdd_progress: {
		current: {
			requests: [
				{
					id: 'question:worker-01.q1',
					kind: 'choose',
					title: 'Storage format',
					prompt: 'Which format should settings use?',
					answer: 'envelope',
					context: 'proposal.md section 3',
					options: [
						{ id: 'a', description: 'Keep TOML', eligible: true, recommended: true },
						{ id: 'b', description: 'Switch to JSON', eligible: true, recommended: false }
					]
				}
			]
		}
	}
} as unknown as components['schemas']['PipelineRunRead'];

test('a worker question is recorded with an option and a decision, never declined', async () => {
	const user = userEvent.setup();
	api.POST.mockResolvedValue({ data: { ...run, state: 'dispatching' } });
	render(SddWorkflowRequests, { run: questionRun, onchange: vi.fn() });
	expect(screen.getByText(/Worker question/)).toBeTruthy();
	expect(screen.getByText(/Context: proposal.md section 3/)).toBeTruthy();
	expect(screen.queryByRole('button', { name: 'Decline' })).toBeNull();
	expect(screen.queryByRole('button', { name: 'Defer decision' })).toBeNull();
	const record = screen.getByRole('button', { name: 'Record answer' }) as HTMLButtonElement;
	expect(record.disabled).toBe(true);
	await user.click(screen.getByLabelText(/Keep TOML/));
	expect(record.disabled).toBe(false);
	await user.type(screen.getByLabelText(/Decision/), 'Keep TOML; tidy key names only');
	await user.click(record);
	expect(api.POST.mock.calls[0][1].body).toMatchObject({
		workflow_answer: { request: 'question:worker-01.q1', action: 'accept', value: 'a' },
		feedback: 'Keep TOML; tidy key names only'
	});
});

test('a question answered outside its options needs a written decision', async () => {
	const user = userEvent.setup();
	api.POST.mockResolvedValue({ data: { ...run, state: 'dispatching' } });
	render(SddWorkflowRequests, { run: questionRun, onchange: vi.fn() });
	const record = screen.getByRole('button', { name: 'Record answer' }) as HTMLButtonElement;
	await user.type(screen.getByLabelText(/Decision/), 'Neither: keep both readers');
	expect(record.disabled).toBe(false);
	await user.click(record);
	expect(api.POST.mock.calls[0][1].body).toMatchObject({
		workflow_answer: { request: 'question:worker-01.q1', action: 'accept', value: null },
		feedback: 'Neither: keep both readers'
	});
});
