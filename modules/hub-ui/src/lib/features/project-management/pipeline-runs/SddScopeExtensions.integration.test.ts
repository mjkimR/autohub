import userEvent from '@testing-library/user-event';
import { cleanup, render, screen } from '@testing-library/svelte';
import { afterEach, expect, test, vi } from 'vitest';
import type { components } from '$lib/api';
import SddRunPanel from './SddRunPanel.svelte';
import SddReportDetails from './SddReportDetails.svelte';

const { api } = vi.hoisted(() => ({ api: { POST: vi.fn(), GET: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

test.each([['docs/proposals/PROP-demo'], ['specs/2026-11/20261105-demo']])(
	'retained scope extension evidence remains inspectable for %s',
	async (unit) => {
		api.GET.mockResolvedValue({ data: [] });
		const proposal = unit.startsWith('docs/proposals/');
		const run = {
			id: 'run-1',
			revision: 3,
			state: 'paused',
			pull_url: 'https://github.com/owner/app/pull/7',
			sdd_snapshot: { provider: 'devkit-spec', spec_dir: unit },
			sdd_progress: {
				head_sha: 'a'.repeat(40),
				base_sha: 'b'.repeat(40),
				unit_status: proposal ? 'reviewing' : 'completed',
				current: {
					stage: { name: 'Approval', human_gate: proposal ? false : 'dev-integration', exit: [] },
					requests: proposal ? [{ id: 'gate:plan-accept', kind: 'approve', answer: 'record' }] : []
				},
				reports: [
					{
						kind: 'worker',
						file: 'envelopes/worker-01.yaml',
						status: 'completed',
						summary: 'Added coverage',
						scope_extensions: [
							{
								path: 'tests/test_retry.py',
								task: 2,
								reason: '<script>Cover retry</script>',
								requirements: ['AC-01', 'AC-02']
							},
							{
								path: 'src/retry.py',
								task: 3,
								reason: 'Update the caller',
								requirements: ['AC-02']
							}
						]
					}
				]
			}
		} as unknown as components['schemas']['PipelineRunRead'];
		render(SddRunPanel, { run });
		await userEvent.setup().click(screen.getByText('Retained native execution evidence'));
		const evidence = screen.getByRole('region', { name: 'Worker scope extensions' });
		expect(evidence.closest('details')?.open).toBe(true);
		expect(evidence.textContent).toContain('tests/test_retry.py');
		expect(evidence.textContent).toContain('src/retry.py');
		expect(evidence.textContent).toContain('Task 2');
		expect(evidence.textContent).toContain('AC-01, AC-02');
		expect(evidence.textContent).toContain('<script>Cover retry</script>');
		expect(evidence.querySelector('script')).toBeNull();
		expect(
			screen.queryByRole('button', { name: /Approve integration|Accept proposal/ })
		).toBeNull();
		expect(api.POST).not.toHaveBeenCalled();
	}
);

test.each([undefined, [], null])(
	'legacy evidence without extensions stays readable (%s)',
	(extensions) => {
		render(SddReportDetails, {
			report: { assumptions: ['API is stable'], scope_extensions: extensions }
		});
		expect(screen.getByText('API is stable')).toBeTruthy();
		expect(screen.queryByRole('region', { name: 'Worker scope extensions' })).toBeNull();
	}
);
