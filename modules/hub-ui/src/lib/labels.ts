/**
 * Display-case label for a raw domain value (a state or status). Labels are written in code, not
 * derived with CSS `capitalize`, so acronyms such as CI, PR, SDD and AI keep their case. A value
 * missing from `labels` (one newer than this client) falls back to sentence case, e.g.
 * `foo_bar` or `foo-bar` → `Foo bar`.
 */
export function displayLabel(value: string, labels: Readonly<Record<string, string>> = {}): string {
	const written = labels[value];
	if (written) return written;
	const words = value.replaceAll(/[_-]+/g, ' ').trim();
	return words.charAt(0).toUpperCase() + words.slice(1);
}
