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
])('embedded roadmap opens selected-branch proposal members of %s', async (milestone) => {
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
	await fireEvent.click(screen.getByRole('button', { name: 'Roadmap' }));
	const member = await screen.findByRole('button', { name: 'Active feature' });
	await fireEvent.click(member);
	expect(selected).toHaveBeenCalledWith(proposal);
	expect(source.tree).toHaveBeenCalledWith(
		'docs/proposals',
		'plan-feature',
		expect.any(AbortSignal)
	);
});
