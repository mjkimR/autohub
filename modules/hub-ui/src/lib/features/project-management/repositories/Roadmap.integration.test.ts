import { cleanup, render, screen, fireEvent } from '@testing-library/svelte';
import { afterEach, expect, test, vi } from 'vitest';
import NativeSddViewer from './documents/NativeSddViewer.svelte';
import { sourceFor } from './documents/fixtures';

afterEach(cleanup);

test.each([
	'docs/roadmap/MS-delivery.md',
	'docs/roadmap/_archive/MS-delivery.md',
	'docs/packages/sdk/roadmap/MS-delivery.md',
	'docs/packages/sdk/roadmap/_archive/MS-delivery.md'
])('embedded progress opens selected-branch proposal members of %s', async (milestone) => {
	const proposal = 'docs/proposals/PROP-feature/proposal.md';
	const documents: Record<string, string> = {
		[milestone]:
			'---\nid: MS-delivery\ntitle: Delivery\nstatus: active\ndepends_on: []\n---\n# Delivery',
		[proposal]:
			'---\nid: PROP-feature\ntitle: Active feature\nstatus: reviewing\nmilestone: MS-delivery\n---\n# Active feature'
	};
	const source = sourceFor(documents);
	const selected = vi.fn();
	render(NativeSddViewer, {
		dataSource: source,
		branch: 'plan-feature',
		onselectpath: selected
	});
	expect(await screen.findByText('plan-feature', { exact: false })).toBeTruthy();
	await fireEvent.click(screen.getByRole('button', { name: 'Progress' }));
	const member = await screen.findByRole('button', { name: 'Active feature' });
	await fireEvent.click(member);
	expect(selected).toHaveBeenCalledWith(proposal);
	expect(source.tree).toHaveBeenCalledWith(
		'docs/proposals',
		'plan-feature',
		expect.any(AbortSignal)
	);
});

test('progress lists specs after milestone groups, newest first, with document status only', async () => {
	const source = sourceFor({
		'docs/roadmap/MS-delivery.md':
			'---\nid: MS-delivery\ntitle: Delivery\nstatus: active\n---\n# D',
		'specs/2026-11/20261101-old/spec.md':
			'---\nid: SPEC-old\ntitle: Old spec\nstatus: completed\n---\n# Old',
		'specs/2026-11/20261117-new/spec.md':
			'---\nid: SPEC-new\ntitle: New spec\nstatus: in-progress\n---\n# New',
		'specs/2026-11/20261117-new/tasks.md': '# Not an anchor'
	});
	render(NativeSddViewer, { dataSource: source, branch: 'main', onselectpath: vi.fn() });
	await fireEvent.click(await screen.findByRole('button', { name: 'Progress' }));
	const specs = await screen.findByRole('region', { name: 'Specs' });
	const titles = Array.from(specs.querySelectorAll('li button')).map((b) => b.textContent?.trim());
	expect(titles).toEqual(['New spec', 'Old spec']);
	expect(screen.getByText('Proposals that finished Development', { exact: false })).toBeTruthy();
	expect(source.blob).not.toHaveBeenCalledWith(
		'specs/2026-11/20261117-new/tasks.md',
		'main',
		expect.any(AbortSignal)
	);
});
