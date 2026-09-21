/** Read an API refusal or FastAPI validation errors without exposing the submitted input. */
export function apiErrorMessage(error: unknown, fallback: string): string {
	if (!error || typeof error !== 'object' || !('detail' in error)) return fallback;
	const detail = error.detail;
	if (typeof detail === 'string' && detail.trim()) return detail;
	if (Array.isArray(detail)) {
		const messages = detail.flatMap((item: unknown) =>
			item &&
			typeof item === 'object' &&
			'msg' in item &&
			typeof item.msg === 'string' &&
			item.msg.trim()
				? [item.msg]
				: []
		);
		if (messages.length > 0) return messages.join('; ');
	}
	return fallback;
}
