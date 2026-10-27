import { cleanup, render, screen, fireEvent } from '@testing-library/svelte';
import { afterEach, expect, test, vi } from 'vitest';
import { SddViewer, type RepositoryDataSource } from 'devkit-viewer';

afterEach(cleanup);

test('embedded roadmap reads the selected branch proposal and opens its unit for execution links', async () => {
	const proposal = 'docs/proposals/PROP-feature/proposal.md';
	const milestone = 'docs/roadmap/MS-delivery.md';
	const documents: Record<string, string> = {
		[milestone]:
			'---\nid: MS-delivery\ntitle: Delivery\nstatus: active\ndepends_on: []\n---\n# Delivery',
		[proposal]:
			'---\nid: PROP-feature\ntitle: Active feature\nstatus: reviewing\nmilestone: MS-delivery\n---\n# Active feature'
	};
	const tree: Record<string, string[]> = {
		'': ['docs'],
		docs: ['docs/roadmap', 'docs/proposals'],
		'docs/roadmap': [milestone],
		'docs/proposals': ['docs/proposals/PROP-feature'],
		'docs/proposals/PROP-feature': [proposal]
	};
	const source: RepositoryDataSource = {
		info: async () => ({ default_branch: 'main' }),
		refs: async () => ({ default_branch: 'main', branches: ['main', 'plan-feature'] }),
		tree: vi.fn(async (path: string, ref: string) => ({
			items: (tree[path.replace(/\/$/, '')] ?? [])
				.filter((p) => ref === 'plan-feature' || !p.startsWith('docs/proposals'))
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
		branch: 'plan-feature',
		initialView: 'roadmap',
		onselectpath: selected
	});
	expect(await screen.findByText('Base: plan-feature branch')).toBeTruthy();
	const member = await screen.findByRole('button', { name: 'Active feature' });
	await fireEvent.click(member);
	expect(selected).toHaveBeenCalledWith(proposal);
	expect(source.tree).toHaveBeenCalledWith(
		'docs/proposals',
		'plan-feature',
		expect.any(AbortSignal)
	);
});
