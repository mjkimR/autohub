import { describe, expect, test } from 'vitest';
import { displayLabel } from './labels';

describe('displayLabel', () => {
	test('a written label wins, so acronyms keep their case', () => {
		expect(displayLabel('awaiting_ci', { awaiting_ci: 'Awaiting CI' })).toBe('Awaiting CI');
	});

	test('an unmapped value falls back to sentence case', () => {
		expect(displayLabel('foo_bar')).toBe('Foo bar');
		expect(displayLabel('conflict-fix', {})).toBe('Conflict fix');
		expect(displayLabel('pending')).toBe('Pending');
	});
});
