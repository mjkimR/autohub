import { afterEach, expect, test, vi } from 'vitest';
import {
	noticeSelection,
	retainNoticeReturn,
	consumeNoticeReturn,
	clearNoticeReturn
} from './notice-return';
afterEach(() => {
	window.sessionStorage.clear();
	window.history.replaceState({}, '', '/');
	vi.restoreAllMocks();
});
const fingerprint = 'a'.repeat(64);
test('retains only exact key/fingerprint and restores once to fixed same origin route', () => {
	window.history.replaceState(
		{},
		'',
		'/decisions?decision_key=entry&decision_fingerprint=' +
			fingerprint +
			'&redirect=https://evil.example'
	);
	retainNoticeReturn();
	window.history.replaceState({}, '', '/?google=complete');
	const path = consumeNoticeReturn();
	expect(path).toContain('/decisions?decision_key=entry');
	expect(path).not.toContain('evil');
	expect(consumeNoticeReturn()).toBeNull();
});
test('expired or malformed selections cannot navigate', () => {
	window.history.replaceState(
		{},
		'',
		'/decisions?decision_key=entry&decision_fingerprint=' + fingerprint
	);
	retainNoticeReturn();
	window.history.replaceState({}, '', '/');
	vi.spyOn(Date, 'now').mockReturnValue(Date.now() + 31 * 60 * 1000);
	expect(consumeNoticeReturn()).toBeNull();
	expect(
		noticeSelection(
			new URL('https://hub.example/decisions?decision_key=a&decision_fingerprint=bad')
		)
	).toBeNull();
});
test('storage refusal preserves normal authentication and clear is safe', () => {
	vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
		throw new Error('denied');
	});
	window.history.replaceState(
		{},
		'',
		'/decisions?decision_key=entry&decision_fingerprint=' + fingerprint
	);
	expect(() => retainNoticeReturn()).not.toThrow();
	expect(() => clearNoticeReturn()).not.toThrow();
});
