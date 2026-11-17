/** HTTP reason phrases and our own fallbacks say nothing the operator can act on. */
const GENERIC =
	/^(internal server error|bad gateway|service unavailable|gateway timeout|an unexpected internal server error occurred\.?|failed to fetch|network ?error|load failed|unable to load\b.*)$/i;

/**
 * An operator-readable read failure: `lead` names what failed and what stayed safe; a specific
 * server or client reason follows it, while bare status phrases are dropped.
 */
export function readableLoadError(error: unknown, lead: string): string {
	const detail = error instanceof Error ? error.message.trim() : '';
	return detail && !GENERIC.test(detail) ? `${lead} ${detail}` : lead;
}
