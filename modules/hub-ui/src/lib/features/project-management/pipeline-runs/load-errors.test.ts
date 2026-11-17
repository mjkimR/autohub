import { expect, test } from 'vitest';
import { readableLoadError } from './load-errors';

const lead = "Couldn't load decisions.";

test('drops bare status phrases and fallbacks', () => {
	expect(readableLoadError(new Error('Internal Server Error'), lead)).toBe(lead);
	expect(readableLoadError(new Error('Unable to load decisions'), lead)).toBe(lead);
	expect(readableLoadError('not an error', lead)).toBe(lead);
});

test('keeps a specific reason after the lead', () => {
	expect(readableLoadError(new Error('Run changed while loading decisions.'), lead)).toBe(
		"Couldn't load decisions. Run changed while loading decisions."
	);
});
