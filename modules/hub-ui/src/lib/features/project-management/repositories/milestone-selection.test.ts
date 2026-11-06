import { expect, test } from 'vitest';
import { orderedSelection, type MilestonePreview } from './milestone-selection';

test('topological order uses canonical identity and cannot include held or nonmembers', () => {
	const preview = {
		complete: true,
		members: ['a', 'b', 'held'].map((id) => ({
			id,
			eligibility: id === 'held' ? 'held' : 'eligible_now'
		})),
		edges: [{ source: 'a', canonical_id: 'b' }]
	} as unknown as MilestonePreview;
	expect(orderedSelection(preview, ['a', 'b', 'held', 'outside']).map((m) => m.id)).toEqual([
		'b',
		'a'
	]);
	expect(orderedSelection({ ...preview, complete: false }, ['a'])).toEqual([]);
});
