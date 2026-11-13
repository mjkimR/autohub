import { expect, test } from 'vitest';
import {
	pendingDecisionPhrase,
	pendingDecisionText,
	summarizePendingDecisions
} from './pending-decisions.svelte';

const row = (actionable: boolean) => ({ actionable });

test('counts only actionable inbox rows', () => {
	const value = summarizePendingDecisions({
		items: [row(true), row(false), row(true)],
		has_more: false
	});
	expect(value).toEqual({ status: 'known', count: 2, lowerBound: false });
	expect(pendingDecisionText(value)).toBe('2');
	expect(pendingDecisionPhrase(value)).toBe('2 pending decisions');
});

test('a full sample with more rows is a lower bound', () => {
	const value = summarizePendingDecisions({ items: [row(true)], has_more: true });
	expect(pendingDecisionText(value)).toBe('1+');
	expect(pendingDecisionPhrase(value)).toBe('1 or more pending decisions');
});

test('one owed decision uses the singular', () => {
	const value = summarizePendingDecisions({ items: [row(true)], has_more: false });
	expect(pendingDecisionPhrase(value)).toBe('1 pending decision');
});

test('zero, unknown and an undecidable sample stay neutral', () => {
	const zero = summarizePendingDecisions({ items: [row(false)], has_more: false });
	expect(zero).toEqual({ status: 'known', count: 0, lowerBound: false });
	expect(pendingDecisionText(zero)).toBe('');
	const undecidable = summarizePendingDecisions({ items: [row(false)], has_more: true });
	expect(undecidable).toEqual({ status: 'unknown' });
	expect(pendingDecisionText({ status: 'unknown' })).toBe('');
	expect(pendingDecisionPhrase({ status: 'unknown' })).toBe('');
});
