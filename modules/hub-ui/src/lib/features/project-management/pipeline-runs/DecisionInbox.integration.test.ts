import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import DecisionInbox from './DecisionInbox.svelte';
const { api } = vi.hoisted(() => ({ api: { GET: vi.fn(), POST: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
const entry = {
	key: 'row',
	run_state: 'blocked',
	pull_number: 7,
	pull_url: 'https://github.com/owner/app/pull/7',
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
	expect(screen.getByRole('link', { name: 'PR #7 ↗' }).getAttribute('href')).toBe(
		'https://github.com/owner/app/pull/7'
	);
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
			body: {
				key: 'row',
				fingerprint: 'fp'
			}
		})
	);
	await user.keyboard('{Escape}');
	await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
	await waitFor(() =>
		expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Review' }))
	);
	expect((screen.getByLabelText('Kind') as HTMLSelectElement).value).toBe('run-question');
});

test('notice selection uses exact lookup outside loaded pages then owner review', async () => {
	const fp = 'a'.repeat(64);
	window.history.replaceState({}, '', '/decisions?decision_key=outside&decision_fingerprint=' + fp);
	const previous = api.GET.getMockImplementation();
	api.GET.mockImplementation(async (path: string, ...args: unknown[]) =>
		path.endsWith('/decisions/selection')
			? { data: { ...entry, key: 'outside', fingerprint: fp } }
			: previous?.(path, ...args)
	);
	render(DecisionInbox);
	await waitFor(() =>
		expect(api.POST).toHaveBeenCalledWith('/api/v1/pipeline-runs/decisions/review', {
			body: { key: 'outside', fingerprint: fp }
		})
	);
	window.history.replaceState({}, '', '/');
});
test('each row carries one labeled status and only operator work is marked for attention', async () => {
	api.GET.mockImplementation(async (path: string) => {
		if (path === '/api/v1/projects') return { data: { items: [] } };
		if (path.endsWith('/decisions'))
			return {
				data: {
					items: [
						{ ...entry, key: 'open', title: 'Open question' },
						{ ...entry, key: 'answered', title: 'Answered question', question_state: 'answered' },
						{
							...entry,
							key: 'publishing',
							title: 'Publishing answer',
							kind: 'native-hub-question',
							actionable: false
						}
					],
					has_more: false,
					next_cursor: null
				}
			};
		return { data: run };
	});
	render(DecisionInbox);
	const row = async (title: string) => (await screen.findByText(title)).closest('article')!;
	const text = (element: Element) => element.textContent?.replace(/\s+/g, ' ') ?? '';

	expect(text(await row('Open question'))).toContain('Needs decision');
	expect(text(await row('Answered question'))).toContain('Answer saved — resume pending');
	expect(text(await row('Publishing answer'))).toContain('Answer publication pending');
	expect((await row('Open question')).getAttribute('data-attention')).toBe('true');
	expect((await row('Answered question')).getAttribute('data-attention')).toBe('true');
	expect((await row('Publishing answer')).hasAttribute('data-attention')).toBe(false);
	expect(document.querySelectorAll('[data-attention]')).toHaveLength(2);
	expect(screen.queryByText('Answer saved', { exact: true })).toBeNull();
});
test('question state filter options use the inbox status labels', async () => {
	render(DecisionInbox);
	await screen.findByText('Choose behavior');
	const options = [...(screen.getByLabelText('Question state') as HTMLSelectElement).options];
	expect(options.map((option) => [option.value, option.text])).toEqual([
		['', 'All states'],
		['open', 'Needs decision'],
		['answered', 'Answer saved — resume pending']
	]);
});
test('rows link the project and PR run in-app and label the run state and kind', async () => {
	render(DecisionInbox);
	const row = (await screen.findByText('Choose behavior')).closest('article')!;
	expect(screen.getByRole('link', { name: 'Application' }).getAttribute('href')).toBe(
		'/projects/project'
	);
	expect(screen.getByRole('link', { name: 'Open PR run for PR #7' }).getAttribute('href')).toBe(
		'/projects/project/runs/run'
	);
	const state = row.querySelector('[data-run-state]')!;
	expect(state.getAttribute('data-run-state')).toBe('blocked');
	expect(state.textContent?.trim()).toBe('Blocked');
	expect(row.textContent).toContain('Run question');
	expect(row.textContent).not.toMatch(/\bblocked\b|run question/);
	const kinds = [...(screen.getByLabelText('Kind') as HTMLSelectElement).options];
	expect(kinds.map((option) => option.text)).toEqual(['All kinds', 'Run question']);
});
