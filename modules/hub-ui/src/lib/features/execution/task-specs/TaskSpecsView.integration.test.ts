import { cleanup, fireEvent, render, screen } from '@testing-library/svelte';
import { afterEach, expect, test, vi } from 'vitest';
import TaskSpecsView from './TaskSpecsView.svelte';

const { api } = vi.hoisted(() => ({ api: { GET: vi.fn() } }));

vi.mock('$lib/api', () => ({ api }));
vi.mock('svelte-sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

test('lists registered tasks and searches names and descriptions', async () => {
	api.GET.mockResolvedValue({
		data: [
			{
				name: 'pipeline.dispatch_project',
				description: 'Observe ready PR runs, then admit a bounded batch of dispatches.',
				payload_schema: { type: 'object', properties: { project_id: { type: 'string' } } }
			},
			{ name: 'jules.sync_sessions', description: '', payload_schema: null }
		]
	});
	render(TaskSpecsView);

	expect(await screen.findByText('pipeline.dispatch_project')).toBeTruthy();
	expect(screen.getByText(/project_id/)).toBeTruthy();
	expect(screen.getByText('No description provided.')).toBeTruthy();

	await fireEvent.input(screen.getByPlaceholderText('Search task specifications...'), {
		target: { value: 'bounded batch' }
	});
	expect(screen.queryByText('jules.sync_sessions')).toBeNull();
	expect(screen.getByText('pipeline.dispatch_project')).toBeTruthy();

	await fireEvent.input(screen.getByPlaceholderText('Search task specifications...'), {
		target: { value: 'nothing matches' }
	});
	expect(screen.getByText('No task specifications registered')).toBeTruthy();
});
