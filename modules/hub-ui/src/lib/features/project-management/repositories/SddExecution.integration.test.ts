import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { session } from '$lib/stores/session.svelte';
import SddExecution from './SddExecution.svelte';

const { api } = vi.hoisted(() => ({ api: { POST: vi.fn(), GET: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
beforeEach(() => {
	session.logout();
	api.POST.mockReset();
	api.GET.mockReset().mockResolvedValue({ data: [] });
});
afterEach(cleanup);

test('starts existing-PR work directly without runtime or readiness probes', async () => {
	api.POST.mockResolvedValue({ data: { id: 'run-1' } });
	render(SddExecution, { projectId: 'project', selectedSpec: 'specs/2026-11/feature' });
	const user = userEvent.setup();
	await user.selectOptions(screen.getByLabelText('Activity effort'), 'high');
	await user.click(screen.getByRole('button', { name: 'Start execution' }));
	await screen.findByRole('link', { name: 'Open PR run' });
	expect(api.POST).toHaveBeenCalledExactlyOnceWith('/api/v1/projects/{project_id}/runs', {
		params: { path: { project_id: 'project' } },
		body: {
			spec_dir: 'specs/2026-11/feature',
			pull_number: 1,
			implemented: false,
			handoff: false,
			activity_effort: 'high'
		}
	});
	expect(screen.queryByRole('button', { name: /Check runtime|Check readiness/ })).toBeNull();
	expect(api.GET.mock.calls.every(([path]) => !/runtime|readiness|milestone/.test(path))).toBe(
		true
	);
});

test('an unknown enrollment freezes the original PR/unit and retries unchanged', async () => {
	api.POST.mockRejectedValueOnce(new Error('Lost connection')).mockResolvedValueOnce({
		data: { id: 'run-2' }
	});
	const view = render(SddExecution, {
		projectId: 'project',
		selectedSpec: 'specs/2026-11/original'
	});
	const user = userEvent.setup();
	await user.click(screen.getByRole('button', { name: 'Start execution' }));
	await screen.findByText('Start outcome unresolved');
	await view.rerender({ projectId: 'project', selectedSpec: 'specs/2026-11/different' });
	expect(screen.getByRole('region', { name: 'Original activity request' }).textContent).toContain(
		'specs/2026-11/original'
	);
	expect(
		(screen.getByRole('button', { name: 'Start execution' }) as HTMLButtonElement).disabled
	).toBe(true);
	await user.click(screen.getByRole('button', { name: 'Retry same request' }));
	await waitFor(() => expect(api.POST).toHaveBeenCalledTimes(2));
	expect(api.POST.mock.calls[1]).toEqual(api.POST.mock.calls[0]);
});
