import { cleanup, render, screen, fireEvent } from '@testing-library/svelte';
import { afterEach, expect, test, vi } from 'vitest';
import { SddViewer, type RepositoryDataSource } from 'devkit-viewer';

afterEach(cleanup);

test.each([
	'docs/roadmap/MS-delivery.md',
	'docs/roadmap/_archive/MS-delivery.md',
	'docs/packages/sdk/roadmap/MS-delivery.md',
	'docs/packages/sdk/roadmap/_archive/MS-delivery.md'
])('embedded roadmap opens selected-branch proposal members of %s', async (milestone) => {
	const proposal = 'docs/proposals/PROP-feature/proposal.md';
	const documents: Record<string, string> = {
		[milestone]:
			'---\nid: MS-delivery\ntitle: Delivery\nstatus: active\ndepends_on: []\n---\n# Delivery',
		[proposal]:
			'---\nid: PROP-feature\ntitle: Active feature\nstatus: reviewing\nmilestone: MS-delivery\n---\n# Active feature'
	};
	const tree: Record<string, string[]> = {};
	for (const path of [milestone, proposal]) {
		const parts = path.split('/');
		for (let i = 0; i < parts.length; i++) {
			const parent = parts.slice(0, i).join('/');
			const child = parts.slice(0, i + 1).join('/');
			if (!(tree[parent] ??= []).includes(child)) tree[parent].push(child);
		}
	}
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
