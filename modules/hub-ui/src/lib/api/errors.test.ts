import { expect, test } from 'vitest';
import { apiErrorCode, apiErrorMessage } from './errors';

test('preserves a backend refusal', () => {
	expect(apiErrorMessage({ detail: 'Project changed; reload' }, 'Failed')).toBe(
		'Project changed; reload'
	);
});

test('formats field validation messages without including submitted values', () => {
	expect(
		apiErrorMessage(
			{
				detail: [
					{ msg: 'Name is required', input: 'private-input' },
					null,
					{ msg: 42 },
					{ msg: 'Interval must be positive', loc: ['body', 'interval_seconds'] }
				]
			},
			'Failed'
		)
	).toBe('Name is required; Interval must be positive');
});

test.each([
	undefined,
	null,
	'not JSON',
	{},
	{ detail: null },
	{ detail: '' },
	{ detail: ' ' },
	{ detail: [] },
	{ detail: [{ msg: null }, { msg: '' }] },
	{ detail: { input: 'private-input' } }
])('falls back for an unexpected error payload: %j', (error) => {
	expect(apiErrorMessage(error, 'Request failed')).toBe('Request failed');
});

test('reads a refusal code only when the error carries one', () => {
	expect(apiErrorCode({ detail: 'Branch exists', code: 'SDD_BRANCH_EXISTS' })).toBe(
		'SDD_BRANCH_EXISTS'
	);
	expect(apiErrorCode({ detail: 'Conflict' })).toBeUndefined();
	expect(apiErrorCode({ code: 42 })).toBeUndefined();
	expect(apiErrorCode(null)).toBeUndefined();
});
