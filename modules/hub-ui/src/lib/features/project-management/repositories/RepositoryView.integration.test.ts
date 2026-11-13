import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import type { components } from '$lib/api';
import RepositoryView from './RepositoryView.svelte';
const { api, page, goto } = vi.hoisted(() => ({
	api: { GET: vi.fn(), POST: vi.fn() },
	page: { url: new URL('http://hub.test/projects/p?tab=repository') },
	goto: vi.fn()
}));
vi.mock('$lib/api', () => ({ api }));
vi.mock('$app/state', async () => {
	const { createSubscriber } = await import('svelte/reactivity');
	let update = () => {};
	const subscribe = createSubscriber((notify) => {
		update = notify;
		return () => {
			update = () => {};
		};
	});
	let current = page.url;
	Object.defineProperty(page, 'url', {
		get() {
			subscribe();
			return current;
		},
		set(value) {
			current = value;
			update();
		},
		configurable: true
	});
	return { page };
});
vi.mock('$app/navigation', () => ({ goto }));
const unit = 'specs/2026-11/20261113-demo';
const batch = '12345678-1234-1234-1234-123456789012';
const project = {
	id: 'p',
	name: 'Project',
	project_type: 'sdd',
	github: { repository: 'owner/app' }
} as components['schemas']['ProjectRead'];
let missing = false;
beforeEach(() => {
	api.GET.mockReset();
	api.POST.mockReset();
	goto.mockReset();
	missing = false;
	page.url = new URL(
		`http://hub.test/projects/p?tab=repository&unit=${encodeURIComponent(unit)}&ref=dev-demo&batch=${batch}`
	);
	api.GET.mockImplementation(
		async (
			path: string,
			options: { params: { query?: { path?: string }; path: { batch_id?: string } } }
		) => {
			if (path.endsWith('/info'))
				return {
					data: { default_branch: 'main', branches: ['main', 'dev-demo'], branches_complete: true }
				};
			if (path.endsWith('/blob'))
				return missing
					? { error: { detail: 'Not found' } }
					: {
							data: {
								path: options.params.query?.path,
								content:
									'---\nid: SPEC-demo\ntitle: Addressed demo\nstatus: planned\n---\n# Addressed demo',
								encoding: 'utf-8',
								size: 100
							}
						};
			if (path.endsWith('/tree')) return { data: { items: [] } };
			if (path.endsWith('/sdd/proposals')) return { data: { items: [] } };
			if (path.endsWith('/sdd/runs')) return { data: [] };
			if (path.endsWith('/{batch_id}'))
				return {
					data: {
						id: options.params.path.batch_id,
						project_id: 'p',
						state: 'stopped',
						revision: 3,
						members: []
					}
				};
			return { data: [] };
		}
	);
});
afterEach(cleanup);

test('direct and reloaded URL select branch, unit and exact batch without mutations', async () => {
	const first = render(RepositoryView, { project });
	await waitFor(() =>
		expect(
			(screen.getByLabelText('Unit directory (spec or proposal)') as HTMLInputElement).value
		).toBe(unit)
	);
	expect((screen.getByLabelText('Repository branch') as HTMLSelectElement).value).toBe('dev-demo');
	expect(
		(await screen.findAllByRole('heading', { name: 'Addressed demo' })).length
	).toBeGreaterThan(0);
	expect(
		await screen.findByRole('heading', { name: `Batch ${batch} · stopped · revision 3` })
	).toBeTruthy();
	expect(
		api.GET.mock.calls.some(([path]) => path === '/api/v1/projects/{project_id}/sdd/batches')
	).toBe(false);
	expect(
		api.GET.mock.calls.some(
			([path, opts]) =>
				path.endsWith('/blob') &&
				opts.params.query.path === `${unit}/spec.md` &&
				opts.params.query.ref === 'dev-demo'
		)
	).toBe(true);
	expect(api.POST).not.toHaveBeenCalled();
	await userEvent.setup().click(screen.getByRole('button', { name: 'Git Browser' }));
	await userEvent.setup().click(screen.getByRole('button', { name: 'Sdd View' }));
	expect(
		(screen.getByLabelText('Unit directory (spec or proposal)') as HTMLInputElement).value
	).toBe(unit);
	first.unmount();
	render(RepositoryView, { project });
	await waitFor(() =>
		expect(
			(screen.getByLabelText('Unit directory (spec or proposal)') as HTMLInputElement).value
		).toBe(unit)
	);
	expect(api.POST).not.toHaveBeenCalled();
});

test('missing and malformed unit cannot expose activity controls while batch remains independently inspectable', async () => {
	missing = true;
	render(RepositoryView, { project });
	expect(await screen.findByRole('heading', { name: 'Unit unavailable' })).toBeTruthy();
	expect(screen.queryByRole('button', { name: 'Start execution' })).toBeNull();
	expect(
		await screen.findByRole('heading', { name: `Batch ${batch} · stopped · revision 3` })
	).toBeTruthy();
	await userEvent.setup().click(screen.getByRole('button', { name: 'Browse repository' }));
	expect(goto).toHaveBeenCalledWith(expect.stringContaining(`batch=${batch}`), expect.anything());
	expect(goto.mock.calls[0][0]).not.toContain('unit=');
	expect(api.POST).not.toHaveBeenCalled();
});

test('deleted recorded branch keeps its name and Browse resets the unavailable ref', async () => {
	page.url = new URL(`http://hub.test/projects/p?tab=repository&unit=${unit}&ref=deleted`);
	render(RepositoryView, { project });
	expect(await screen.findByRole('heading', { name: 'Unit unavailable' })).toBeTruthy();
	expect(screen.getByText(/Repository branch deleted is unavailable/)).toBeTruthy();
	await userEvent.setup().click(screen.getByRole('button', { name: 'Browse repository' }));
	expect(goto.mock.calls[0][0]).toBe('/projects/p?tab=repository');
	expect(api.POST).not.toHaveBeenCalled();
});

test('same-project browser query navigation replaces selected unit and preserves independent batch', async () => {
	render(RepositoryView, { project });
	await waitFor(() =>
		expect(
			(screen.getByLabelText('Unit directory (spec or proposal)') as HTMLInputElement).value
		).toBe(unit)
	);
	const next = 'docs/proposals/PROP-next';
	page.url = new URL(
		`http://hub.test/projects/p?tab=repository&unit=${next}&ref=main&batch=${batch}`
	);
	await waitFor(() =>
		expect(
			(screen.getByLabelText('Unit directory (spec or proposal)') as HTMLInputElement).value
		).toBe(next)
	);
	expect((screen.getByLabelText('Repository branch') as HTMLSelectElement).value).toBe('main');
	expect(
		await screen.findByRole('heading', { name: `Batch ${batch} · stopped · revision 3` })
	).toBeTruthy();
	page.url = new URL(
		`http://hub.test/projects/p?tab=repository&unit=${unit}&ref=dev-demo&batch=${batch}`
	);
	await waitFor(() =>
		expect(
			(screen.getByLabelText('Unit directory (spec or proposal)') as HTMLInputElement).value
		).toBe(unit)
	);
	expect(api.POST).not.toHaveBeenCalled();
});
