export type NoticeSelection = { key: string; fingerprint: string };
const storageKey = 'autohub.notice-return';
const ttl = 30 * 60 * 1000;

export function noticeSelection(url: URL): NoticeSelection | null {
	const key = url.searchParams.get('decision_key');
	const fingerprint = url.searchParams.get('decision_fingerprint');
	if (!key || key.length > 255 || !fingerprint || !/^[a-f0-9]{64}$/.test(fingerprint)) return null;
	return { key, fingerprint };
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
		/* Authentication remains usable without storage. */
	}
}
export function consumeNoticeReturn(): string | null {
	const current = noticeSelection(new URL(window.location.href));
	try {
		const raw = window.sessionStorage.getItem(storageKey);
		window.sessionStorage.removeItem(storageKey);
		if (current) return selectionPath(current);
		if (!raw) return null;
		const value = JSON.parse(raw);
		if (typeof value.at !== 'number' || value.at > Date.now() || Date.now() - value.at > ttl)
			return null;
		const candidate = noticeSelection(new URL(selectionPath(value), 'https://local.invalid'));
		return candidate ? selectionPath(candidate) : null;
	} catch {
		return current ? selectionPath(current) : null;
	}
}
export function clearNoticeReturn() {
	try {
		window.sessionStorage.removeItem(storageKey);
	} catch {
		/* Nothing authoritative is stored here. */
	}
}
