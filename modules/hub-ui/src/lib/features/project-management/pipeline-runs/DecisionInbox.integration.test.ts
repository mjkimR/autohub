import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import DecisionInbox from './DecisionInbox.svelte';
const { api } = vi.hoisted(() => ({ api: { GET: vi.fn(), POST: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
const entry = {
	key: 'row',
	run_id: 'run',
	project_id: 'project',
	kind: 'run-question',
	subject_id: 'q',
	fingerprint: 'fp',
	title: 'Choose behavior',
	question_state: 'open',
	actionable: true,
	waiting_since: '2026-11-05T00:00:00Z',
	observed_at: '2026-11-05T00:00:00Z',
	revision: 1,
	head_sha: null
};
const run = {
	id: 'run',
	revision: 1,
	state: 'blocked',
	pull_number: 7,
	pull_url: 'https://github.com/owner/app/pull/7',
	pull_snapshot: { title: 'Owner review' }
};
beforeEach(() => {
	api.GET.mockReset();
	api.POST.mockReset();
	api.GET.mockImplementation(async (path: string) => {
		if (path === '/api/v1/projects')
			return { data: { items: [{ id: 'project', name: 'Application' }] } };
		if (path.endsWith('/decisions'))
			return { data: { items: [entry], has_more: true, next_cursor: 'next' } };
		if (path.endsWith('/questions'))
			return {
				data: {
					items: [
						{
							id: 'q',
							question: 'Choose behavior',
							state: 'open',
							answers: [],
							actor: 'user',
							created_at: entry.waiting_since
						}
					],
					total_count: 1,
					run_revision: 1
				}
			};
		if (path.endsWith('/{question_id}'))
			return {
				data: {
					id: 'q',
					question: 'Choose behavior',
					state: 'open',
					answers: [],
					actor: 'user',
					created_at: entry.waiting_since
				}
			};
		return { data: run };
	});
	api.POST.mockResolvedValue({ data: run });
});
afterEach(() => {
	cleanup();
	document.body.innerHTML = '';
	document.body.removeAttribute('style');
});
test('filters reset paging and pages use the retained cursor', async () => {
	const user = userEvent.setup();
	render(DecisionInbox);
	await screen.findByText('Choose behavior');
	await user.selectOptions(screen.getByLabelText('Kind'), 'run-question');
	await waitFor(() =>
		expect(api.GET).toHaveBeenLastCalledWith('/api/v1/pipeline-runs/decisions', {
			params: { query: expect.objectContaining({ kind: 'run-question', cursor: undefined }) }
		})
	);
	await user.click(screen.getByRole('button', { name: 'Next' }));
	expect(api.GET).toHaveBeenLastCalledWith('/api/v1/pipeline-runs/decisions', {
		params: { query: expect.objectContaining({ kind: 'run-question', cursor: 'next' }) }
	});
	await user.click(screen.getByRole('button', { name: 'Refresh' }));
	expect(api.GET).toHaveBeenLastCalledWith('/api/v1/pipeline-runs/decisions', {
		params: { query: expect.objectContaining({ cursor: undefined }) }
	});
});
test('closing exact owner review retains filters and returns row focus', async () => {
	const user = userEvent.setup();
	render(DecisionInbox);
	await screen.findByText('Choose behavior');
	await user.selectOptions(screen.getByLabelText('Kind'), 'run-question');
	await user.click(screen.getByRole('button', { name: 'Review' }));
	await screen.findByRole('dialog');
	await waitFor(() =>
		expect(api.POST).toHaveBeenCalledWith('/api/v1/pipeline-runs/decisions/review', {
			body: { key: 'row', fingerprint: 'fp' }
		})
	);
	await user.keyboard('{Escape}');
	await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
	await waitFor(() =>
		expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Review' }))
	);
	expect((screen.getByLabelText('Kind') as HTMLSelectElement).value).toBe('run-question');
});
