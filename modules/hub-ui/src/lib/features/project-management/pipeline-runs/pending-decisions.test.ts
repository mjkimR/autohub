import { expect, test } from 'vitest';
import {
	isPendingDecisionUnknown,
	pendingDecisionPhrase,
	pendingDecisionText,
	summarizePendingDecisions
} from './pending-decisions.svelte';

test('uses the exact backend count', () => {
	const value = summarizePendingDecisions({ actionable_total_count: 137 });
	expect(value).toEqual({ status: 'known', count: 137 });
	expect(pendingDecisionText(value)).toBe('137');
	expect(pendingDecisionPhrase(value)).toBe('137 pending decisions');
});

test('one owed decision uses the singular', () => {
	const value = summarizePendingDecisions({ actionable_total_count: 1 });
	expect(pendingDecisionText(value)).toBe('1');
	expect(pendingDecisionPhrase(value)).toBe('1 pending decision');
});

test('only an unknown count is marked unknown; zero is known', () => {
	expect(isPendingDecisionUnknown({ status: 'unknown' })).toBe(true);
	expect(isPendingDecisionUnknown({ status: 'known', count: 0 })).toBe(false);
	expect(isPendingDecisionUnknown({ status: 'known', count: 3 })).toBe(false);
});

test('zero and unknown carry no count text', () => {
	const zero = summarizePendingDecisions({ actionable_total_count: 0 });
	expect(zero).toEqual({ status: 'known', count: 0 });
	expect(pendingDecisionText(zero)).toBe('');
	expect(pendingDecisionPhrase(zero)).toBe('');
	expect(pendingDecisionText({ status: 'unknown' })).toBe('');
	expect(pendingDecisionPhrase({ status: 'unknown' })).toBe('');
});

test.each([undefined, -1, 1.5, Number.NaN])('an invalid count (%s) is unknown', (count) => {
	expect(summarizePendingDecisions({ actionable_total_count: count })).toEqual({
		status: 'unknown'
	});
});
