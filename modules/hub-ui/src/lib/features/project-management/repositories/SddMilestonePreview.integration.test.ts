import { cleanup, render, screen, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import SddMilestonePreview from './SddMilestonePreview.svelte';

const { api } = vi.hoisted(() => ({ api: { POST: vi.fn(), GET: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
afterEach(cleanup);
const props = { projectId: 'project', repository: 'owner/repo', currentRef: 'feature' };
function result(complete = true) {
	return {
		project_id: 'project',
		repository: 'owner/repo',
		requested_ref: 'feature',
		resolved_sha: 'a'.repeat(40),
		milestone: { id: 'MS-demo', status: 'planned', path: 'docs/roadmap/MS-demo.md' },
		observed_at: '2026-11-05T00:00:00Z',
		runtime_identity: 'devkit:locked',
		complete,
		counts: { members: 3, anchors: 0, edges: 0 },
		limits: { members: 50, anchors: 200, edges: 500, deadline_seconds: 150 },
		reasons: complete ? [] : ['Partial catalog'],
		warnings: [],
		nodes: [],
		edges: [],
		members: ['PROP-z', 'PROP-a', 'PROP-held'].map((id) => ({
			id,
			title: id,
			path: `docs/proposals/${id}/proposal.md`,
			status: 'draft',
			activity_kind: 'plan',
			stage: 'direction',
			admission: 'pass',
			scheduling: id === 'PROP-held' ? 'held' : 'pass',
			workflow_hold: {},
			eligibility: id === 'PROP-held' ? 'held' : 'eligible_now',
			reasons: [],
			evidence: []
		}))
	};
}
beforeEach(() => {
	api.GET.mockReset().mockResolvedValue({
		data: {
			resolved_sha: 'a'.repeat(40),
			complete: true,
			reasons: [],
			items: [
				{ id: 'MS-demo', title: 'Demo', status: 'planned' },
				{ id: 'MS-other', title: 'Other', status: 'planned' }
			]
		}
	});
	api.POST.mockReset().mockResolvedValue({ data: result() });
});
async function inspect() {
	const user = userEvent.setup();
	await screen.findByRole('option', { name: /MS-demo/ });
	await user.selectOptions(screen.getByLabelText('Milestone'), 'MS-demo');
	await user.click(screen.getByRole('button', { name: 'Preview milestone' }));
	return user;
}

test('starts empty and orders only explicitly selected eligible activities', async () => {
	render(SddMilestonePreview, props);
	const user = await inspect();
	const held = await screen.findByRole('checkbox', { name: 'Select PROP-held' });
	expect((held as HTMLInputElement).disabled).toBe(true);
	const summary = screen.getByLabelText('Selected activities');
	expect(within(summary).getByText('Selected activities (0)')).toBeTruthy();
	await user.click(screen.getByRole('checkbox', { name: 'Select PROP-z' }));
	await user.click(screen.getByRole('checkbox', { name: 'Select PROP-a' }));
	expect(
		within(summary)
			.getAllByRole('listitem')
			.map((e) => e.textContent)
	).toEqual(['PROP-a · Planning', 'PROP-z · Planning']);
	expect(api.POST).toHaveBeenCalledTimes(1);
	expect(api.POST.mock.calls[0][0]).toBe('/api/v1/projects/{project_id}/sdd/milestone-preview');
	expect(screen.queryByRole('button', { name: /start execution/i })).toBeNull();
	await user.click(screen.getByRole('button', { name: 'Clear selection' }));
	expect(within(summary).queryAllByRole('listitem')).toHaveLength(0);
});

test('incomplete preview exposes reasons and disables every selection and order', async () => {
	api.POST.mockResolvedValue({ data: result(false) });
	render(SddMilestonePreview, props);
	await inspect();
	expect((await screen.findByRole('alert')).textContent).toContain('Partial catalog');
	expect(screen.getAllByRole('checkbox').every((e) => (e as HTMLInputElement).disabled)).toBe(true);
	expect(screen.queryByLabelText('Selected activities')).toBeNull();
});

test.each(['currentRef', 'projectId', 'refresh'] as const)(
	'context %s clears selection and ignores delayed responses',
	async (key) => {
		let resolve!: (value: unknown) => void;
		api.POST.mockReturnValueOnce(
			new Promise((done) => {
				resolve = done;
			})
		);
		const view = render(SddMilestonePreview, props);
		await inspect();
		await view.rerender({ ...props, [key]: key === 'refresh' ? 1 : 'other' });
		resolve({ data: result() });
		await screen.findByRole('option', { name: /MS-demo/ });
		expect(screen.queryByRole('checkbox')).toBeNull();
		expect(screen.queryByLabelText('Selected activities')).toBeNull();
		expect(api.POST.mock.calls[0][1].signal.aborted).toBe(true);
	}
);

test('milestone change and refresh discard selected and obsolete response state', async () => {
	const view = render(SddMilestonePreview, props);
	const user = await inspect();
	await screen.findByRole('checkbox', { name: 'Select PROP-a' });
	await user.click(screen.getByRole('checkbox', { name: 'Select PROP-a' }));
	let resolve!: (value: unknown) => void;
	api.POST.mockReturnValueOnce(
		new Promise((done) => {
			resolve = done;
		})
	);
	await user.click(screen.getByRole('button', { name: 'Refresh preview' }));
	expect(screen.queryByRole('checkbox')).toBeNull();
	await user.selectOptions(screen.getByLabelText('Milestone'), 'MS-other');
	resolve({ data: result() });
	await view.rerender(props);
	expect(screen.queryByRole('checkbox')).toBeNull();
});
