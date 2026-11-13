import { expect, test } from 'vitest';
import {
	decisionPhrase,
	decisionText,
	owedPhrase,
	owedText,
	summarizeOwedCounts
} from './owed-counts.svelte';

test('uses the exact counted total and the decision part of the same response', () => {
	const value = summarizeOwedCounts({
		total: 7,
		by_kind: { decision: 2, 'stopped-run': 5, 'failed-run': 3 },
		by_project: { p1: 7 }
	});
	expect(value).toEqual({
		status: 'known',
		total: 7,
		byKind: { decision: 2, 'stopped-run': 5, 'failed-run': 3 },
		byProject: { p1: 7 }
	});
	expect(owedText(value)).toBe('7');
	expect(owedPhrase(value)).toBe('7 items need you');
	expect(decisionText(value)).toBe('2');
	expect(decisionPhrase(value)).toBe('2 pending decisions');
});

test('zero and unknown carry no text', () => {
	const zero = summarizeOwedCounts({ total: 0, by_kind: { 'failed-run': 4 }, by_project: {} });
	expect(zero.status).toBe('known');
	for (const value of [zero, { status: 'unknown' } as const]) {
		expect(owedText(value)).toBe('');
		expect(owedPhrase(value)).toBe('');
		expect(decisionText(value)).toBe('');
		expect(decisionPhrase(value)).toBe('');
	}
});

test('singular phrases', () => {
	const value = summarizeOwedCounts({ total: 1, by_kind: { decision: 1 }, by_project: {} });
	expect(owedPhrase(value)).toBe('1 item needs you');
	expect(decisionPhrase(value)).toBe('1 pending decision');
});

test.each([undefined, -1, 1.5, Number.NaN])('an invalid total (%s) is unknown', (total) => {
	expect(summarizeOwedCounts({ total, by_kind: {}, by_project: {} } as never)).toEqual({
		status: 'unknown'
	});
});

test('a missing response is unknown and invalid per-kind values are dropped', () => {
	expect(summarizeOwedCounts(undefined)).toEqual({ status: 'unknown' });
	const value = summarizeOwedCounts({
		total: 2,
		by_kind: { decision: -3, 'stopped-run': 2 },
		by_project: {}
	});
	expect(value).toMatchObject({ byKind: { 'stopped-run': 2 } });
});
