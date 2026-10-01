import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import WorkPlanActivity from './WorkPlanActivity.svelte';

const { api } = vi.hoisted(() => ({ api: { GET: vi.fn(), POST: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
const event = {
	id: 'e1',
	kind: 'updated',
	actor: 'machine:planner',
	revision: 2,
	body: 'Refined the scope',
	created_at: '2026-10-01T00:00:00Z',
	changes: { title: { before: 'Idea', after: 'Ready plan' } }
};
beforeEach(() => {
	api.GET.mockReset().mockResolvedValue({ data: { items: [event], total_count: 1 } });
	api.POST.mockReset().mockResolvedValue({ data: { ...event, kind: 'comment', changes: {} } });
});
afterEach(cleanup);

async function open() {
	render(WorkPlanActivity, { projectId: 'p1', planId: 'plan1', revision: 2 });
	expect(api.GET).not.toHaveBeenCalled();
	const details = screen.getByText('Activity and comments').closest('details')!;
	details.open = true;
	await fireEvent(details, new Event('toggle'));
	await screen.findByText('Refined the scope');
}

test('loads on demand and filters comments without making write requests', async () => {
	await open();
	expect(screen.getByText(/machine:planner/)).toBeTruthy();
	expect(screen.getByText(/Ready plan/)).toBeTruthy();
	await fireEvent.click(screen.getByLabelText('Comments only'));
	await waitFor(() =>
		expect(api.GET).toHaveBeenLastCalledWith(
			'/api/v1/projects/{project_id}/work-plans/{plan_id}/activity',
			{
				params: {
					path: { project_id: 'p1', plan_id: 'plan1' },
					query: { offset: 0, limit: 25, comments_only: true }
				}
			}
		)
	);
	expect(api.POST).not.toHaveBeenCalled();
});

test('failed comment retries retain text and identity without issuing controls', async () => {
	await open();
	api.POST.mockResolvedValueOnce({ error: { detail: 'Response unavailable' } });
	await fireEvent.input(screen.getByLabelText('Comment'), {
		target: { value: 'Keep this context' }
	});
	await fireEvent.click(screen.getByRole('button', { name: 'Add comment' }));
	await screen.findByRole('alert');
	const first = api.POST.mock.calls[0];
	expect((screen.getByLabelText('Comment') as HTMLTextAreaElement).value).toBe('Keep this context');
	await fireEvent.click(screen.getByRole('button', { name: 'Add comment' }));
	await waitFor(() => expect(api.POST).toHaveBeenCalledTimes(2));
	expect(api.POST.mock.calls[1]).toEqual(first);
	expect(first[0]).toBe('/api/v1/projects/{project_id}/work-plans/{plan_id}/comments');
	await waitFor(() =>
		expect((screen.getByLabelText('Comment') as HTMLTextAreaElement).value).toBe('')
	);
});
