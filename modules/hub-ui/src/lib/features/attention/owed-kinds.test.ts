import { expect, test } from 'vitest';
import { OWED_KINDS, catalogHoldText, groupOwedItems, waitingAge } from './owed-kinds';
import { owedItem } from './owed-fixtures';

test('groups follow consequence order and failed runs close the list quietly', () => {
	expect(OWED_KINDS.map((entry) => entry.kind)).toEqual([
		'decision',
		'stopped-run',
		'work-plan-proposed',
		'work-item-recovery',
		'work-item-replacement',
		'work-item-attention',
		'sdd-batch-attention',
		'connection-test-cleanup',
		'failed-run'
	]);
	expect(OWED_KINDS.filter((entry) => entry.quiet).map((entry) => entry.kind)).toEqual([
		'failed-run'
	]);
});

test('loaded items are grouped in that order and empty kinds are left out', () => {
	const groups = groupOwedItems([
		owedItem('failed-run'),
		owedItem('connection-test-cleanup'),
		owedItem('decision'),
		owedItem('decision', { subject: { id: 'run-question:q2' } })
	]);
	expect(groups.map((group) => [group.kind, group.items.length])).toEqual([
		['decision', 2],
		['connection-test-cleanup', 1],
		['failed-run', 1]
	]);
});

test.each([
	['2026-11-12T09:29:40Z', 'under 1 min'],
	['2026-11-12T09:18:00Z', '12 min'],
	['2026-11-12T04:30:00Z', '5 h'],
	['2026-11-09T09:30:00Z', '3 d'],
	['2026-11-12T10:00:00Z', 'under 1 min']
])('waiting since %s reads %s', (since, text) => {
	expect(waitingAge(since, Date.parse('2026-11-12T09:30:00Z'))).toBe(text);
});

test('catalog holds read as context with their reason', () => {
	const id = '66666666-6666-4666-8666-666666666666';
	expect(catalogHoldText({ catalog_id: id, reason: 'unavailable' })).toBe(
		'AI catalog is unavailable'
	);
	expect(
		catalogHoldText({
			catalog_id: id,
			reason: 'quota-blocked',
			available_at: '2026-11-12T12:00:00Z'
		})
	).toMatch(/^AI catalog quota is exhausted until /);
});
