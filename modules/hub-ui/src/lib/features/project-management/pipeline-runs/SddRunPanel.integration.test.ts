import { cleanup, render, screen } from '@testing-library/svelte';
import { afterEach, expect, test } from 'vitest';
import type { components } from '$lib/api';
import SddRunPanel from './SddRunPanel.svelte';
afterEach(cleanup);
const run = {
	id: 'run',
	pull_url: 'https://github.com/team/repo/pull/2',
	state: 'blocked',
	pull_snapshot: { head_sha: 'a'.repeat(40) },
	sdd_snapshot: { provider: 'repository-agent', spec_dir: 'docs/proposals/PROP-demo' },
	sdd_progress: { current: { stage: { human_gate: 'dev-integration' } }, reports: [] }
} as unknown as components['schemas']['PipelineRunRead'];
test('optimistic context points to ordinary questions and CI without interpreting stages', () => {
	render(SddRunPanel, {
		run: {
			...run,
			sdd_snapshot: {
				...run.sdd_snapshot,
				provider: 'repository-agent',
				activity_kind: 'plan'
			}
		}
	});
	expect(screen.getByText(/agent owns repository setup and workflow execution/)).toBeTruthy();
	expect(screen.queryByText('Retained native execution evidence')).toBeNull();
	expect(screen.queryByText('dev-integration')).toBeNull();
});
