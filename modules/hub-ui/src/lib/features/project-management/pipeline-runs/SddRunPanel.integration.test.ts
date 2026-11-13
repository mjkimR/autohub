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
	sdd_snapshot: { provider: 'devkit-spec', spec_dir: 'docs/proposals/PROP-demo' },
	sdd_progress: { current: { stage: { human_gate: 'dev-integration' } }, reports: [] }
} as unknown as components['schemas']['PipelineRunRead'];
test('legacy evidence is labeled retired and exposes no workflow decision controls', () => {
	render(SddRunPanel, { run });
	expect(screen.getByText('Retired · read only')).toBeTruthy();
	expect(
		screen.queryByRole('button', { name: /Approve|Reject|Revoke|Request changes|Resume/ })
	).toBeNull();
	expect(screen.getByText('Retained native execution evidence')).toBeTruthy();
});
test('optimistic context points to ordinary questions and CI without interpreting stages', () => {
	render(SddRunPanel, {
		run: {
			...run,
			sdd_snapshot: {
				...run.sdd_snapshot,
				execution_version: 2,
				provider: 'repository-agent',
				activity_kind: 'plan'
			}
		}
	});
	expect(screen.getByText(/agent owns repository setup and workflow execution/)).toBeTruthy();
	expect(screen.queryByText('Retained native execution evidence')).toBeNull();
	expect(screen.queryByText('dev-integration')).toBeNull();
});
