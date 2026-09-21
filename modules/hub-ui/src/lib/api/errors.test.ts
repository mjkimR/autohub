import { expect, test } from 'vitest';
import { apiErrorMessage } from './errors';

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
