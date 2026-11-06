export type NoticeSelection = { key: string; fingerprint: string };
export type NoticeReturnOutcome = {
	path: string | null;
	reason: 'unavailable' | 'expired' | 'invalid' | 'missing' | null;
};
const storageKey = 'autohub.notice-return';
const ttl = 30 * 60 * 1000;
export function noticeSelection(url: URL): NoticeSelection | null {
	const key = url.searchParams.get('decision_key');
	const fingerprint = url.searchParams.get('decision_fingerprint');
	return key && key.length <= 255 && fingerprint && /^[a-f0-9]{64}$/.test(fingerprint)
		? { key, fingerprint }
		: null;
}
export function selectionPath(value: NoticeSelection) {
	return (
		'/decisions?' +
		new URLSearchParams({ decision_key: value.key, decision_fingerprint: value.fingerprint })
	);
}
export function retainNoticeReturn() {
	const selection = noticeSelection(new URL(window.location.href));
	if (!selection) return;
	try {
		window.sessionStorage.setItem(storageKey, JSON.stringify({ ...selection, at: Date.now() }));
	} catch {
		/* The approved login completion explains unavailable notice recovery. */
	}
}
export function consumeNoticeReturnOutcome(expected = false): NoticeReturnOutcome {
	const current = noticeSelection(new URL(window.location.href));
	try {
		const raw = window.sessionStorage.getItem(storageKey);
		window.sessionStorage.removeItem(storageKey);
		if (current) return { path: selectionPath(current), reason: null };
		if (!raw) return { path: null, reason: expected ? 'missing' : null };
		const value = JSON.parse(raw);
		if (
			!value ||
			typeof value !== 'object' ||
			typeof value.key !== 'string' ||
			typeof value.fingerprint !== 'string' ||
			typeof value.at !== 'number'
		)
			return { path: null, reason: 'invalid' };
		if (value.at > Date.now() || Date.now() - value.at > ttl)
			return { path: null, reason: 'expired' };
		const selected = noticeSelection(new URL(selectionPath(value), 'https://local.invalid'));
		return selected
			? { path: selectionPath(selected), reason: null }
			: { path: null, reason: 'invalid' };
	} catch {
		return current
			? { path: selectionPath(current), reason: null }
			: { path: null, reason: 'unavailable' };
	}
}
export function consumeNoticeReturn() {
	return consumeNoticeReturnOutcome().path;
}
export function clearNoticeReturn() {
	try {
		window.sessionStorage.removeItem(storageKey);
	} catch {
		/* No authority is stored here. */
	}
}
export const noticeRecoveryGuidance =
	'Reopen original notice to review the exact decision. The prior notice-return identity is unavailable; sign-in still succeeded.';
