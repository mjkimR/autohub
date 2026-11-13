/** Sections of the PR run page that a link can land on. */
export type RunSection = 'decisions' | 'attempts' | 'next-step';

/**
 * Canonical PR run page URL. Without a known project the `/runs/<id>` route resolves the
 * project and redirects, so callers that only hold a run id still reach the same page.
 */
export function runHref(runId: string, projectId?: string | null, section?: RunSection): string {
	const id = encodeURIComponent(runId);
	const path = projectId ? `/projects/${encodeURIComponent(projectId)}/runs/${id}` : `/runs/${id}`;
	return section ? `${path}#${section}` : path;
}

/**
 * Old deep links named a run on a list route: `/projects/runs?run=<id>[&view=decisions]` and
 * `/projects/<id>?tab=runs&run=<id>`. Returns the run page URL they now mean, or null.
 */
export function legacyRunRedirect(search: string): string | null {
	const params = new URLSearchParams(search);
	const runId = params.get('run');
	if (!runId) return null;
	return runHref(runId, null, params.get('view') === 'decisions' ? 'decisions' : undefined);
}

/** Addressed subjects are browse requests and convey no execution authority. */
export function repositorySubjectHref(
	projectId: string,
	subject: { unit?: string; ref?: string; batch?: string }
): string {
	const params = new URLSearchParams({ tab: 'repository' });
	if (subject.unit) params.set('unit', subject.unit);
	if (subject.ref) params.set('ref', subject.ref);
	if (subject.batch) params.set('batch', subject.batch);
	return `/projects/${encodeURIComponent(projectId)}?${params}`;
}
