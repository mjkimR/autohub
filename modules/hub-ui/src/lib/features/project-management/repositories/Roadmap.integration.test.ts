import { cleanup, render, screen, fireEvent } from '@testing-library/svelte';
import { afterEach, expect, test, vi } from 'vitest';
import { SddViewer, type RepositoryDataSource } from 'devkit-viewer';

afterEach(cleanup);

test('embedded roadmap reads an in-progress branch and opens its unit for execution links', async () => {
	const spec = 'specs/2026-10/20261019-feature/spec.md';
	const milestone = 'docs/roadmap/MS-delivery.md';
	const documents: Record<string, string> = {
		[milestone]:
			'---\nid: MS-delivery\ntitle: Delivery\nstatus: active\ndepends_on: []\n---\n# Delivery',
		[spec]:
			'---\nid: SPEC-feature\ntitle: Active feature\nstatus: active\nmilestone: MS-delivery\n---\n# Active feature'
	};
	const tree: Record<string, string[]> = {
		'': ['docs', 'specs'],
		docs: ['docs/roadmap'],
		'docs/roadmap': [milestone],
		specs: ['specs/2026-10'],
		'specs/2026-10': ['specs/2026-10/20261019-feature'],
		'specs/2026-10/20261019-feature': [spec]
	};
	const source: RepositoryDataSource = {
		info: async () => ({ default_branch: 'main' }),
		refs: async () => ({ default_branch: 'main', branches: ['main', 'dev-feature'] }),
		tree: vi.fn(async (path: string, ref: string) => ({
			items: (tree[path.replace(/\/$/, '')] ?? [])
				.filter((p) => ref === 'dev-feature' || !p.startsWith('specs'))
				.map((p) => ({
					name: p.split('/').pop(),
					path: p,
					type: p.endsWith('.md') ? 'file' : 'dir'
				}))
		})),
		blob: async (path: string) => ({ path, content: documents[path] ?? '', encoding: 'utf-8' })
	};
	const selected = vi.fn();
	render(SddViewer, {
		dataSource: source,
		branch: 'dev-feature',
		initialView: 'roadmap',
		onselectpath: selected
	});
	expect(await screen.findByText('작업 브랜치 1개 포함')).toBeTruthy();
	const member = await screen.findByRole('button', { name: 'Active feature' });
	await fireEvent.click(member);
	expect(selected).toHaveBeenCalledWith(spec);
	expect(source.tree).toHaveBeenCalledWith('specs', 'dev-feature', expect.any(AbortSignal));
});
