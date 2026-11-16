import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { tick } from 'svelte';
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
	goto.mockReset().mockImplementation(async (url: string) => {
		page.url = new URL(url, 'http://hub.test');
	});
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
		expect(screen.getByRole('region', { name: 'Selected SDD unit' }).textContent).toContain(unit)
	);
	expect((screen.getByLabelText('Repository branch') as HTMLSelectElement).value).toBe('dev-demo');
	expect(
		(await screen.findAllByRole('heading', { name: 'Addressed demo' })).length
	).toBeGreaterThan(0);
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
	await userEvent.setup().click(screen.getByRole('button', { name: 'SDD View' }));
	expect(screen.getByRole('region', { name: 'Selected SDD unit' }).textContent).toContain(unit);
	first.unmount();
	render(RepositoryView, { project });
	await waitFor(() =>
		expect(screen.getByRole('region', { name: 'Selected SDD unit' }).textContent).toContain(unit)
	);
	expect(api.POST).not.toHaveBeenCalled();
});

test('missing and malformed unit cannot expose activity controls ', async () => {
	missing = true;
	render(RepositoryView, { project });
	expect(await screen.findByRole('heading', { name: 'Unit unavailable' })).toBeTruthy();
	expect(screen.queryByRole('button', { name: 'Enroll PR' })).toBeNull();
	await userEvent.setup().click(screen.getByRole('button', { name: 'Browse repository' }));
	expect(goto).toHaveBeenCalledWith(expect.stringContaining('tab=repository'), expect.anything());
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

test('same-project browser query navigation replaces selected unit', async () => {
	render(RepositoryView, { project });
	await waitFor(() =>
		expect(screen.getByRole('region', { name: 'Selected SDD unit' }).textContent).toContain(unit)
	);
	const next = 'docs/proposals/PROP-next';
	page.url = new URL(
		`http://hub.test/projects/p?tab=repository&unit=${next}&ref=main&batch=${batch}`
	);
	await waitFor(() =>
		expect(screen.getByRole('region', { name: 'Selected SDD unit' }).textContent).toContain(next)
	);
	expect((screen.getByLabelText('Repository branch') as HTMLSelectElement).value).toBe('main');
	page.url = new URL(
		`http://hub.test/projects/p?tab=repository&unit=${unit}&ref=dev-demo&batch=${batch}`
	);
	await waitFor(() =>
		expect(screen.getByRole('region', { name: 'Selected SDD unit' }).textContent).toContain(unit)
	);
	expect(api.POST).not.toHaveBeenCalled();
});

test('ordinary selected branch survives Hub SDD Refresh without a ref query', async () => {
	page.url = new URL('http://hub.test/projects/p?tab=repository');
	render(RepositoryView, { project });
	await waitFor(() =>
		expect((screen.getByLabelText('Repository branch') as HTMLSelectElement).value).toBe('main')
	);
	await userEvent.setup().selectOptions(screen.getByLabelText('Repository branch'), 'dev-demo');
	await userEvent.setup().click(screen.getAllByRole('button', { name: 'Refresh' })[0]);
	await waitFor(() =>
		expect((screen.getByLabelText('Repository branch') as HTMLSelectElement).value).toBe('dev-demo')
	);
});

test('pending directory response is discarded immediately after same-project invalid-address navigation', async () => {
	page.url = new URL('http://hub.test/projects/p?tab=repository');
	const original = api.GET.getMockImplementation()!;
	let finish!: (value: unknown) => void;
	api.GET.mockImplementation((path, options) =>
		path.endsWith('/tree') && options.params.query.path === ''
			? new Promise((resolve) => {
					finish = resolve;
				})
			: original(path, options)
	);
	render(RepositoryView, { project });
	await waitFor(() => expect(finish).toBeTypeOf('function'));
	page.url = new URL('http://hub.test/projects/p?tab=repository&unit=../invalid&ref=deleted');
	await screen.findByRole('heading', { name: 'Unit unavailable' });
	await userEvent.setup().click(screen.getByRole('button', { name: 'Git Browser' }));
	finish({
		data: {
			items: [
				{
					name: 'stale-response.txt',
					path: 'stale-response.txt',
					type: 'file',
					size: 10,
					sha: 'stale'
				}
			]
		}
	});
	await tick();
	await tick();
	expect(screen.queryByRole('button', { name: 'stale-response.txt' })).toBeNull();
	expect(screen.queryByText('stale-response.txt')).toBeNull();
});

test('file URL restores its exact branch and browser navigation replaces the document without submission', async () => {
	page.url = new URL('http://hub.test/projects/p?tab=repository&path=docs/guide.md&ref=dev-demo');
	render(RepositoryView, { project });
	await screen.findByRole('heading', { name: 'Addressed demo', level: 1 });
	expect(
		api.GET.mock.calls.some(
			([path, opts]) =>
				path.endsWith('/blob') &&
				opts.params.query.path === 'docs/guide.md' &&
				opts.params.query.ref === 'dev-demo'
		)
	).toBe(true);
	page.url = new URL('http://hub.test/projects/p?tab=repository&path=docs/next.md&ref=dev-demo');
	await waitFor(() =>
		expect(
			api.GET.mock.calls.some(
				([path, opts]) => path.endsWith('/blob') && opts.params.query.path === 'docs/next.md'
			)
		).toBe(true)
	);
	expect(api.POST).not.toHaveBeenCalled();
});

test('browser history clears an addressed unit and its activity controls at a path-less URL', async () => {
	page.url = new URL(
		'http://hub.test/projects/p?tab=repository&path=docs/proposals/PROP-demo/proposal.md&ref=main'
	);
	render(RepositoryView, { project });
	await screen.findByRole('button', { name: 'Start Planning' });
	page.url = new URL('http://hub.test/projects/p?tab=repository&ref=main');
	await waitFor(() =>
		expect(screen.queryByRole('region', { name: 'Selected SDD unit' })).toBeNull()
	);
	expect(screen.queryByRole('button', { name: 'Start Planning' })).toBeNull();
	expect(api.POST).not.toHaveBeenCalled();
});

test('changing a document section clears its obsolete address without submitting work', async () => {
	page.url = new URL(
		'http://hub.test/projects/p?tab=repository&path=docs/proposals/PROP-demo/proposal.md&ref=main'
	);
	render(RepositoryView, { project });
	await screen.findByRole('button', { name: 'Start Planning' });
	await userEvent.setup().click(screen.getByRole('button', { name: 'Documents' }));
	await waitFor(() => expect(page.url.searchParams.has('path')).toBe(false));
	expect(screen.queryByRole('region', { name: 'Selected SDD unit' })).toBeNull();
	expect(api.POST).not.toHaveBeenCalled();
});

test('Git Browser file selection synchronizes its address and restores it across mode switches and reload', async () => {
	page.url = new URL('http://hub.test/projects/p?tab=repository&ref=main');
	const original = api.GET.getMockImplementation()!;
	api.GET.mockImplementation((path, options) =>
		path.endsWith('/tree')
			? Promise.resolve({
					data: {
						items: [{ name: 'guide.md', path: 'docs/guide.md', type: 'file', size: 10, sha: 's' }]
					}
				})
			: original(path, options)
	);
	const first = render(RepositoryView, { project });
	const user = userEvent.setup();
	await screen.findByRole('button', { name: 'Git Browser' });
	await user.click(screen.getByRole('button', { name: 'Git Browser' }));
	await user.click(await screen.findByText('guide.md'));
	await waitFor(() => expect(page.url.searchParams.get('path')).toBe('docs/guide.md'));
	await user.click(screen.getByRole('button', { name: 'SDD View' }));
	await screen.findByRole('heading', { name: 'Addressed demo', level: 1 });
	await user.click(screen.getByRole('button', { name: 'Git Browser' }));
	await waitFor(() => expect(screen.getByText('docs/guide.md')).toBeTruthy());
	first.unmount();
	render(RepositoryView, { project });
	await screen.findByRole('heading', { name: 'Addressed demo', level: 1 });
	expect(page.url.searchParams.get('path')).toBe('docs/guide.md');
	expect(api.POST).not.toHaveBeenCalled();
});
