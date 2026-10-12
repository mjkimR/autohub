import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import SpecrigRunLinks from './SpecrigRunLinks.svelte';
const { api } = vi.hoisted(() => ({ api: { GET: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
beforeEach(() => api.GET.mockReset());
afterEach(cleanup);

test('links only the selected spec and ignores a late response for the previous selection', async () => {
	let finish!: (value: unknown) => void;
	api.GET.mockImplementationOnce(
		() =>
			new Promise((resolve) => {
				finish = resolve;
			})
	);
	api.GET.mockResolvedValueOnce({
		data: [
			{ id: 'new-run', state: 'paused', pull_number: 7, pull_snapshot: { title: 'Current spec' } }
		]
	});
	const view = render(SpecrigRunLinks, { projectId: 'project', specDir: 'specs/2026-10/old' });
	await waitFor(() => expect(api.GET).toHaveBeenCalledOnce());
	await view.rerender({ projectId: 'project', specDir: 'specs/2026-10/new' });
	expect(await screen.findByRole('link', { name: /Current spec/ })).toBeTruthy();
	finish({
		data: [
			{ id: 'old-run', state: 'completed', pull_number: 8, pull_snapshot: { title: 'Old spec' } }
		]
	});
	await Promise.resolve();
	expect(screen.queryByText('Old spec')).toBeNull();
	expect(screen.getByRole('link', { name: /Current spec/ }).getAttribute('href')).toBe(
		'/projects/runs?run=new-run&view=decisions'
	);
	expect(api.GET.mock.calls[1][1].params.query.spec_dir).toBe('specs/2026-10/new');
});
