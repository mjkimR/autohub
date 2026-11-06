import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import WorkItemReplacement from './WorkItemReplacement.svelte';
import type { components } from '$lib/api';
const { api } = vi.hoisted(() => ({ api: { GET: vi.fn(), POST: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
const original = {
	plan_id: 'plan',
	item_id: 'a',
	key: 'a',
	title: 'Original',
	description: 'Original spec',
	acceptance: 'Original checks',
	digest: 'original-digest',
	plan_revision: 5,
	plan_state: 'active',
	item_state: 'failed',
	repository: 'o/r',
	connector_id: 'connector',
	target: 'main',
	branch: 'dev-a',
	execution_id: 'old',
	pull_number: 1,
	pull_url: 'https://github.com/o/r/pull/1',
	merge_sha: null,
	completed_at: null
};
const candidate = {
	...original,
	plan_id: 'replacement-plan',
	item_id: 'r',
	key: 'r',
	title: 'Replacement',
	description: 'Replacement spec',
	digest: 'replacement-digest',
	plan_revision: 8,
	item_state: 'succeeded',
	execution_id: 'replacement-run',
	pull_number: 2,
	pull_url: 'https://github.com/o/r/pull/2',
	merge_sha: 'merge-sha',
	completed_at: '2026-11-06T00:00:00Z'
};
const item = {
	id: 'a',
	key: 'a',
	state: 'failed',
	title: 'Original',
	description: 'Original spec',
	acceptance: 'Checks',
	detail: null,
	branch: null,
	attach_branch: null,
	pull_number: null,
	pull_url: null,
	merge_sha: null,
	pipeline_run_id: null,
	pipeline_run_retired_at: null,
	started_at: null,
	completed_at: null,
	issue: null,
	recovery: null,
	depends_on: []
} as components['schemas']['WorkItemRead'];
const dependent = { id: 'b', key: 'b', depends_on: ['a'] } as components['schemas']['WorkItemRead'];
const empty = { original, candidate: null, evidence_revision: 3, links: [], result: null };
const link = {
	id: 'link1',
	active: true,
	snapshot: { original, replacement: candidate },
	current_replacement: candidate,
	actor: 'user:operator',
	reason: 'Reviewed',
	acceptances: [],
	events: []
};
const linked = {
	...empty,
	links: [link],
	evidence_revision: 4,
	original: { ...original, plan_revision: 6 }
};
const refresh = vi.fn();
beforeEach(() => {
	sessionStorage.clear();
	api.GET.mockReset().mockResolvedValue({ data: empty });
	api.POST.mockReset();
	refresh.mockReset().mockResolvedValue(undefined);
});
afterEach(cleanup);
function mount() {
	return render(WorkItemReplacement, {
		projectId: 'project',
		planId: 'plan',
		item,
		items: [item, dependent],
		refresh
	});
}
async function load() {
	await fireEvent.click(screen.getByRole('button', { name: 'Inspect replacement evidence' }));
	await screen.findByText(/Plan revision 5/);
}
async function reviewCandidate() {
	api.GET.mockResolvedValueOnce({ data: { ...empty, candidate } });
	await fireEvent.input(screen.getByLabelText('Replacement Work Item ID'), {
		target: { value: 'r' }
	});
	await fireEvent.click(screen.getByRole('button', { name: 'Review replacement' }));
	await screen.findByText('Replacement spec');
	await fireEvent.click(screen.getByRole('button', { name: 'Link replacement' }));
}
async function reason() {
	await fireEvent.input(screen.getByLabelText('Replacement reason'), {
		target: { value: 'Reviewed exact specifications' }
	});
	await fireEvent.click(screen.getByRole('checkbox'));
}

test('requires explicit specification review and binds revisions for linking', async () => {
	mount();
	await load();
	await reviewCandidate();
	expect(
		(screen.getByRole('button', { name: 'Confirm replacement decision' }) as HTMLButtonElement)
			.disabled
	).toBe(true);
	await reason();
	api.POST.mockResolvedValue({ data: { ...linked, result: { operation: 'link' } } });
	await fireEvent.click(screen.getByRole('button', { name: 'Confirm replacement decision' }));
	await waitFor(() => expect(api.POST).toHaveBeenCalledOnce());
	expect(api.POST.mock.calls[0][1].body).toMatchObject({
		replacement_item_id: 'r',
		expected_original_revision: 5,
		expected_replacement_revision: 8,
		expected_evidence_revision: 3,
		reason: 'Reviewed exact specifications'
	});
	expect(await screen.findByText(/Recorded link/)).toBeTruthy();
});

test('retains exact request after response loss and blocks replacement input', async () => {
	mount();
	await load();
	await reviewCandidate();
	await reason();
	api.POST.mockRejectedValueOnce(new Error('response lost'));
	await fireEvent.click(screen.getByRole('button', { name: 'Confirm replacement decision' }));
	await screen.findByRole('button', { name: 'Retry same request' });
	const first = api.POST.mock.calls[0][1];
	expect((screen.getByLabelText('Replacement Work Item ID') as HTMLInputElement).disabled).toBe(
		true
	);
	api.GET.mockResolvedValueOnce({
		data: { ...empty, original: { ...original, plan_revision: 99 } }
	});
	await fireEvent.click(screen.getByRole('button', { name: 'Inspect replacement evidence' }));
	await screen.findByText(/Plan revision 99/);
	api.POST.mockResolvedValueOnce({ data: { ...linked, result: { operation: 'link' } } });
	await fireEvent.click(screen.getByRole('button', { name: 'Retry same request' }));
	await waitFor(() => expect(api.POST).toHaveBeenCalledTimes(2));
	expect(api.POST.mock.calls[1][1]).toEqual(first);
});

test('accepts exactly one existing edge with displayed digest and merge identity', async () => {
	api.GET.mockResolvedValueOnce({ data: linked });
	mount();
	await fireEvent.click(screen.getByRole('button', { name: 'Inspect replacement evidence' }));
	await screen.findByText(/Plan revision 6/);
	await fireEvent.click(screen.getByRole('button', { name: 'Review edge acceptance' }));
	await fireEvent.change(screen.getByLabelText('Dependent edge'), { target: { value: 'b' } });
	await reason();
	api.POST.mockResolvedValueOnce({ data: { ...linked, result: { operation: 'accept' } } });
	await fireEvent.click(screen.getByRole('button', { name: 'Confirm replacement decision' }));
	await waitFor(() => expect(api.POST).toHaveBeenCalledOnce());
	expect(api.POST.mock.calls[0][1].body).toMatchObject({
		dependent_item_id: 'b',
		original_digest: 'original-digest',
		replacement_digest: 'replacement-digest',
		merge_sha: 'merge-sha',
		execution_id: 'replacement-run'
	});
});

test('keeps recorded acknowledgement when Plan refresh fails', async () => {
	mount();
	await load();
	await reviewCandidate();
	await reason();
	refresh.mockRejectedValueOnce(new Error('refresh failed'));
	api.POST.mockResolvedValueOnce({ data: { ...linked, result: { operation: 'link' } } });
	await fireEvent.click(screen.getByRole('button', { name: 'Confirm replacement decision' }));
	expect(await screen.findByText(/Recorded link/)).toBeTruthy();
	expect((await screen.findByRole('alert')).textContent).toContain('Recorded; Plan refresh failed');
	expect(screen.queryByRole('button', { name: 'Retry same request' })).toBeNull();
});

test('refused conflict requires refreshed explicit review, with no automatic retry', async () => {
	mount();
	await load();
	await reviewCandidate();
	await reason();
	api.POST.mockResolvedValueOnce({
		response: { status: 409 },
		error: { code: 'REPLACEMENT_CONFLICT', detail: 'stale' }
	});
	await fireEvent.click(screen.getByRole('button', { name: 'Confirm replacement decision' }));
	expect(await screen.findByText(/Refused. Refresh evidence/)).toBeTruthy();
	expect(api.POST).toHaveBeenCalledOnce();
	expect(screen.queryByRole('button', { name: 'Retry same request' })).toBeNull();
	expect(screen.queryByRole('button', { name: 'Confirm replacement decision' })).toBeNull();
});

test('consumed acceptance disables withdrawal and exposes retained history', async () => {
	api.GET.mockResolvedValueOnce({
		data: {
			...linked,
			links: [
				{
					...link,
					acceptances: [
						{
							id: 'accept1',
							dependent_item_id: 'b',
							active: true,
							consumed: true,
							snapshot: link.snapshot,
							actor: 'user:operator',
							reason: 'Reviewed'
						}
					],
					events: [
						{ id: 'event1', kind: 'consumed', actor: 'system', reason: 'Admission', revision: 5 }
					]
				}
			]
		}
	});
	mount();
	await fireEvent.click(screen.getByRole('button', { name: 'Inspect replacement evidence' }));
	await screen.findByText(/Dependent b · consumed/);
	expect(
		(screen.getByRole('button', { name: 'Withdraw link' }) as HTMLButtonElement).disabled
	).toBe(true);
	expect(screen.queryByRole('button', { name: 'Withdraw edge acceptance' })).toBeNull();
	expect(screen.getByRole('link', { name: 'Inspect replacement PR' }).getAttribute('href')).toBe(
		candidate.pull_url
	);
});

test('candidate changes and evidence refresh invalidate prior confirmation', async () => {
	mount();
	await load();
	await reviewCandidate();
	await reason();
	expect(
		(screen.getByRole('button', { name: 'Confirm replacement decision' }) as HTMLButtonElement)
			.disabled
	).toBe(false);
	api.GET.mockResolvedValueOnce({
		data: { ...empty, candidate: { ...candidate, item_id: 'r2', key: 'r2' } }
	});
	await fireEvent.input(screen.getByLabelText('Replacement Work Item ID'), {
		target: { value: 'r2' }
	});
	await fireEvent.click(screen.getByRole('button', { name: 'Review replacement' }));
	await screen.findByText(/r2: Replacement/);
	const old = screen.queryByRole('button', {
		name: 'Confirm replacement decision'
	}) as HTMLButtonElement | null;
	expect(old === null || old.disabled).toBe(true);
	await fireEvent.click(screen.getByRole('button', { name: 'Link replacement' }));
	await reason();
	api.GET.mockResolvedValueOnce({ data: empty });
	await fireEvent.click(screen.getByRole('button', { name: 'Inspect replacement evidence' }));
	await waitFor(() =>
		expect(screen.queryByRole('button', { name: 'Confirm replacement decision' })).toBeNull()
	);
	expect(api.POST).not.toHaveBeenCalled();
});

test('unresolved request survives remount and reload storage restoration', async () => {
	const view = mount();
	await load();
	await reviewCandidate();
	await reason();
	api.POST.mockRejectedValueOnce(new Error('lost'));
	await fireEvent.click(screen.getByRole('button', { name: 'Confirm replacement decision' }));
	await screen.findByRole('button', { name: 'Retry same request' });
	const first = api.POST.mock.calls[0];
	view.unmount();
	mount();
	expect(await screen.findByRole('button', { name: 'Retry same request' })).toBeTruthy();
	api.POST.mockResolvedValueOnce({ data: { ...linked, result: { operation: 'link' } } });
	await fireEvent.click(screen.getByRole('button', { name: 'Retry same request' }));
	await waitFor(() => expect(api.POST).toHaveBeenCalledTimes(2));
	expect(api.POST.mock.calls[1]).toEqual(first);
	expect(sessionStorage.getItem('work-item-replacement:project:a')).toBeNull();
});

test('paginates decision history and shows retained merge and event times', async () => {
	const event = {
		id: 'event1',
		kind: 'link',
		actor: 'user:operator',
		reason: 'Reviewed',
		revision: 1,
		created_at: '2026-11-06T01:00:00Z',
		evidence: {},
		acceptance_id: null
	};
	const page = {
		...linked,
		history_offset: 0,
		history_total_count: 11,
		history_limit: 10,
		links: [{ ...link, event_offset: 0, event_total_count: 2, events: [event] }]
	};
	api.GET.mockResolvedValueOnce({ data: page });
	mount();
	await fireEvent.click(screen.getByRole('button', { name: 'Inspect replacement evidence' }));
	expect(await screen.findByText(/Merge completed: 2026-11-06T00:00:00Z/)).toBeTruthy();
	expect(screen.getByText(/2026-11-06T01:00:00Z/)).toBeTruthy();
	api.GET.mockResolvedValueOnce({
		data: {
			...page,
			links: [
				{
					...page.links[0],
					event_offset: 1,
					events: [{ ...event, id: 'event2', kind: 'withdraw', created_at: '2026-11-06T02:00:00Z' }]
				}
			]
		}
	});
	await fireEvent.click(screen.getByRole('button', { name: 'Load more replacement events' }));
	await screen.findByText(/2026-11-06T02:00:00Z/);
	expect(api.GET.mock.calls[1][1].params.query).toMatchObject({
		event_link_id: 'link1',
		event_offset: 1,
		offset: 0
	});
	api.GET.mockResolvedValueOnce({ data: { ...page, history_offset: 10 } });
	await fireEvent.click(screen.getByRole('button', { name: 'Next replacement links' }));
	await screen.findByRole('button', { name: 'Previous replacement links' });
	expect(api.GET.mock.calls[2][1].params.query.offset).toBe(10);
});

test('lost response then authentication refusal preserves exact request through remount', async () => {
	const view = mount();
	await load();
	await reviewCandidate();
	await reason();
	api.POST.mockRejectedValueOnce(new Error('response lost'));
	await fireEvent.click(screen.getByRole('button', { name: 'Confirm replacement decision' }));
	await screen.findByRole('button', { name: 'Retry same request' });
	const first = api.POST.mock.calls[0];
	api.POST.mockResolvedValueOnce({ response: { status: 401 }, error: { detail: 'Sign in again' } });
	await fireEvent.click(screen.getByRole('button', { name: 'Retry same request' }));
	await screen.findByRole('alert');
	expect(sessionStorage.getItem('work-item-replacement:project:a')).not.toBeNull();
	view.unmount();
	mount();
	await screen.findByRole('button', { name: 'Retry same request' });
	api.POST.mockResolvedValueOnce({ data: { ...linked, result: { operation: 'link' } } });
	await fireEvent.click(screen.getByRole('button', { name: 'Retry same request' }));
	await waitFor(() => expect(api.POST).toHaveBeenCalledTimes(3));
	expect(api.POST.mock.calls[2]).toEqual(first);
});

test('accumulated history retains earlier withdrawn edge context', async () => {
	const withdrawn = {
		id: 'withdrawn1',
		dependent_item_id: 'b',
		active: false,
		consumed: false,
		snapshot: link.snapshot,
		actor: 'user:operator',
		reason: 'Earlier review'
	};
	const event = {
		id: 'event1',
		kind: 'withdraw',
		actor: 'user:operator',
		reason: 'Earlier withdrawal',
		revision: 2,
		created_at: '2026-11-06T01:00:00Z',
		evidence: {},
		acceptance_id: 'withdrawn1'
	};
	const page = {
		...linked,
		history_offset: 0,
		history_total_count: 0,
		history_limit: 10,
		links: [
			{ ...link, event_offset: 0, event_total_count: 2, events: [event], acceptances: [withdrawn] }
		]
	};
	api.GET.mockResolvedValueOnce({ data: page });
	mount();
	await fireEvent.click(screen.getByRole('button', { name: 'Inspect replacement evidence' }));
	await screen.findByText(/Dependent b · withdrawn/);
	api.GET.mockResolvedValueOnce({
		data: {
			...page,
			links: [
				{
					...page.links[0],
					acceptances: [],
					event_offset: 1,
					events: [{ ...event, id: 'event2', acceptance_id: null, kind: 'link' }]
				}
			]
		}
	});
	await fireEvent.click(screen.getByRole('button', { name: 'Load more replacement events' }));
	await waitFor(() => expect(api.GET).toHaveBeenCalledTimes(2));
	expect(screen.queryByText(/Dependent b · withdrawn/)).not.toBeNull();
});
