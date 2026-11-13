import { beforeEach, expect, test, vi } from 'vitest';
import { RepositorySelection } from './repository-selection.svelte';
const { api } = vi.hoisted(() => ({ api: { GET: vi.fn() } }));
vi.mock('$lib/api', () => ({ api }));
const unit = 'specs/2026-11/20261113-demo';
beforeEach(() => {
	api.GET.mockReset();
});
const info = { default_branch: 'main', branches: ['main', 'dev-demo'], branches_complete: true };
function reads() {
	api.GET.mockImplementation(
		async (path: string, options: { params: { query?: { path: string } } }) =>
			path.endsWith('/info')
				? { data: info }
				: { data: { path: options.params.query?.path, content: '# Spec', encoding: 'utf-8' } }
	);
}

test('recognized unit is validated on its recorded branch and survives repeated selection', async () => {
	reads();
	const state = new RepositorySelection();
	await state.select('one', true, unit, 'dev-demo');
	expect(state.status).toBe('ready');
	expect(state.unit).toBe(unit);
	expect(state.ref).toBe('dev-demo');
	expect(api.GET).toHaveBeenCalledWith(
		'/api/v1/projects/{project_id}/repository/blob',
		expect.objectContaining({
			params: { path: { project_id: 'one' }, query: { path: `${unit}/spec.md`, ref: 'dev-demo' } }
		})
	);
	await state.select('one', true, unit, '');
	expect(state.ref).toBe('main');
	expect(state.unit).toBe(unit);
});

test.each(['../secret', 'specs/2026-11/../other', 'docs/random.md', 'specs/2026-11/demo/spec.md'])(
	'rejects arbitrary address %s before repository reads',
	async (path) => {
		const state = new RepositorySelection();
		await state.select('one', true, path, 'main');
		expect(state.status).toBe('unavailable');
		expect(state.unit).toBe('');
		expect(api.GET).not.toHaveBeenCalled();
	}
);

test('missing branch does not fall back or expose an execution selection', async () => {
	reads();
	const state = new RepositorySelection();
	await state.select('one', true, unit, 'deleted');
	expect(state.status).toBe('unavailable');
	expect(state.missingRef).toBe(true);
	expect(state.ref).toBe('deleted');
	expect(state.unit).toBe('');
	expect(api.GET).toHaveBeenCalledTimes(1);
});

test('missing unit and non-SDD project do not select a subject; retry can recover', async () => {
	const state = new RepositorySelection();
	await state.select('one', false, unit, 'main');
	expect(state.status).toBe('unavailable');
	api.GET.mockResolvedValueOnce({ data: info }).mockResolvedValueOnce({
		error: { detail: 'Not found' }
	});
	await state.select('one', true, unit, 'main');
	expect(state.status).toBe('error');
	expect(state.unit).toBe('');
	reads();
	await state.select('one', true, unit, 'main');
	expect(state.status).toBe('ready');
});

test('old unit and project reads cannot overwrite a new address', async () => {
	let finish!: (value: unknown) => void;
	api.GET.mockResolvedValueOnce({ data: info }).mockImplementationOnce(
		() =>
			new Promise((resolve) => {
				finish = resolve;
			})
	);
	const state = new RepositorySelection();
	const pending = state.select('old', true, unit, 'main');
	await vi.waitFor(() => expect(finish).toBeTypeOf('function'));
	reads();
	await state.select('new', true, 'docs/proposals/PROP-current', 'dev-demo');
	finish({ data: { content: '# stale' } });
	await pending;
	expect(state.unit).toBe('docs/proposals/PROP-current');
	expect(state.ref).toBe('dev-demo');
});
