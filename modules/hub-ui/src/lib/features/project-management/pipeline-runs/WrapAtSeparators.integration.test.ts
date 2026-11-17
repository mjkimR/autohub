import { cleanup, render } from '@testing-library/svelte';
import { afterEach, expect, test } from 'vitest';
import WrapAtSeparators from './WrapAtSeparators.svelte';
afterEach(cleanup);

test('offers line breaks only after separators and keeps the text intact', () => {
	const { container } = render(WrapAtSeparators, {
		text: 'docs/proposals/PROP-refund-idempotency'
	});
	expect(container.textContent).toBe('docs/proposals/PROP-refund-idempotency');
	expect(container.querySelectorAll('wbr')).toHaveLength(4);
});
