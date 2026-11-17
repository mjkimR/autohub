import { cleanup, render, screen, within } from '@testing-library/svelte';
import { afterEach, expect, test } from 'vitest';
import type { components } from '$lib/api';
import SddRunPanel from './SddRunPanel.svelte';
afterEach(cleanup);
const run = {
	id: 'run',
	pull_url: 'https://github.com/team/repo/pull/2',
	state: 'paused',
	pull_snapshot: { head_sha: 'b'.repeat(40) },
	sdd_snapshot: {
		provider: 'repository-agent',
		spec_dir: 'docs/proposals/PROP-demo',
		activity_kind: 'plan'
	}
} as unknown as components['schemas']['PipelineRunRead'];
const question = {
	id: 'q',
	head_sha: 'a'.repeat(40),
	source: 'agent',
	answers: []
} as unknown as components['schemas']['QuestionRead'];

test('binds evidence to the question head without interpreting repository stages', () => {
	render(SddRunPanel, { run, question });
	expect(screen.getByText('aaaaaaaa')).toBeTruthy();
	expect(screen.getByRole('link', { name: /Open unit at this head/ }).getAttribute('href')).toBe(
		`https://github.com/team/repo/tree/${'a'.repeat(40)}/docs/proposals/PROP-demo`
	);
	expect(screen.getByRole('link', { name: /View PR changes/ }).getAttribute('href')).toBe(
		'https://github.com/team/repo/pull/2/files'
	);
	expect(screen.queryByText('dev-integration')).toBeNull();
});

test('shows the gate track with text states, not color alone', () => {
	render(SddRunPanel, {
		run,
		question: {
			...question,
			answers: [{ id: 'a', applied_attempt_id: null }]
		} as unknown as components['schemas']['QuestionRead']
	});
	const track = within(screen.getByRole('list', { name: 'Gate progress' }));
	expect(track.getByText(/^Save an answer/).textContent).toContain('(done)');
	expect(track.getByText(/^Resume with the answer/).textContent).toContain('(current step)');
	expect(screen.getByText(/mark the PR Ready in GitHub/)).toBeTruthy();
});
