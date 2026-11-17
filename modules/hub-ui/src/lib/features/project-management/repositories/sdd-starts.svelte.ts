import { api, type components } from '$lib/api';
import { apiErrorCode, apiErrorMessage } from '$lib/api/errors';
import { session } from '$lib/stores/session.svelte';

type ActivityRequest = components['schemas']['StartActivityRequest'];
type Enrollment = components['schemas']['EnrollPullRequest'];
export type StartIntent =
	| {
			kind: 'activity';
			project: string;
			slug: string;
			activity: 'plan' | 'dev';
			body: ActivityRequest;
	  }
	| { kind: 'enroll'; project: string; body: Enrollment };

/** A definitive refusal: the request granted no work and is not retained for retry. */
export type StartRefusal = {
	title: string;
	detail: string;
	/** The existing activity branch Hub refused to overwrite (UC-start-sdd-activity 3a). */
	branch?: string;
	/** A project configuration refusal (UC-start-sdd-activity 2a). */
	configuration?: boolean;
};

/** The SDD unit directory an intent targets. */
export function intentUnit(intent: StartIntent): string {
	return intent.kind === 'activity'
		? `docs/proposals/PROP-${intent.slug}`
		: (intent.body.spec_dir ?? '');
}

/** Operator-facing name of the requested work. */
export function intentLabel(intent: StartIntent): string {
	if (intent.kind === 'enroll') return `Enrollment of PR #${intent.body.pull_number}`;
	return intent.activity === 'plan' ? 'Planning' : 'Development';
}

const CLAIM_PATH = /\/sdd\/claims\/([0-9a-f-]{36})\b/i;

/**
 * Classify a failed start (OPS-sdd-activity-start-refusals). A claim path in the detail or an
 * `SDD_ACTIVITY_OWNED` code names a retained owner; `SDD_BRANCH_EXISTS` and any other 4xx refusal
 * granted no work; a missing response or a server failure leaves the outcome uncertain.
 */
export function classifyStartFailure(
	status: number | undefined,
	code: string | undefined,
	detail: string
) {
	const claimId = detail.match(CLAIM_PATH)?.[1] ?? '';
	if (status === undefined || status >= 500) return { outcome: 'uncertain' as const, claimId };
	if (code === 'SDD_BRANCH_EXISTS') return { outcome: 'refused' as const, claimId: '' };
	if ((status === 409 || status === 410) && (claimId || code === 'SDD_ACTIVITY_OWNED'))
		return { outcome: 'retained' as const, claimId };
	return { outcome: 'refused' as const, claimId: '' };
}

const states: Record<string, SddStarts> = {};

/** Share unresolved intent across the proposal and existing-PR panels in one project. */
export function sddStarts(project: string) {
	const prefix = `${session.generation}:`;
	for (const key of Object.keys(states)) if (!key.startsWith(prefix)) delete states[key];
	const key = `${prefix}${project}`;
	return (states[key] ||= new SddStarts());
}

export class SddStarts {
	pending = $state<StartIntent | null>(null);
	lastKind = $state<StartIntent['kind'] | null>(null);
	/** Unit and work label of the latest request, kept after it resolves for local feedback. */
	lastUnit = $state('');
	lastLabel = $state('');
	busy = $state(false);
	error = $state('');
	message = $state('');
	/** Workspace-level notice after a retained owner was reconciled. */
	resolved = $state('');
	refusal = $state<StartRefusal | null>(null);
	runId = $state('');
	claimId = $state('');
	ownerConflict = $state(false);
	/** Increments when a request settles, so the unit panel can move focus to its outcome. */
	outcomeVersion = $state(0);

	async activity(project: string, slug: string, activity: 'plan' | 'dev', body: ActivityRequest) {
		if (this.pending || this.busy) return;
		await this.begin({ kind: 'activity', project, slug, activity, body: { ...body } });
	}

	async enroll(project: string, body: Enrollment) {
		if (this.pending || this.busy) return;
		await this.begin({ kind: 'enroll', project, body: { ...body } });
	}

	private async begin(intent: StartIntent) {
		this.runId = '';
		this.error = this.message = this.resolved = this.claimId = '';
		this.refusal = null;
		this.ownerConflict = false;
		this.lastKind = intent.kind;
		this.lastUnit = intentUnit(intent);
		this.lastLabel = intentLabel(intent);
		this.pending = intent;
		await this.retry();
	}

	async retry() {
		const intent = this.pending;
		if (!intent || this.busy) return;
		this.busy = true;
		this.error = '';
		this.message = '';
		try {
			const response =
				intent.kind === 'activity'
					? await api.POST(
							intent.activity === 'plan'
								? '/api/v1/projects/{project_id}/sdd/proposals/{slug}/planning'
								: '/api/v1/projects/{project_id}/sdd/proposals/{slug}/development',
							{
								params: { path: { project_id: intent.project, slug: intent.slug } },
								body: intent.body
							}
						)
					: await api.POST('/api/v1/projects/{project_id}/runs', {
							params: { path: { project_id: intent.project } },
							body: intent.body
						});
			if (!response.data) {
				this.fail(intent, response.response.status, response.error);
				return;
			}
			this.runId = response.data.id;
			this.message =
				intent.kind === 'activity'
					? `${intentLabel(intent)} registered. Hub opened a Draft PR and a PR run; the agent follows the repository workflow.`
					: `PR #${intent.body.pull_number} enrolled. Follow its PR run; the agent follows the repository workflow.`;
			this.pending = null;
			this.ownerConflict = false;
			this.claimId = '';
		} catch (error) {
			// No response at all: the outcome is unknown and the exact request stays retained.
			this.error =
				error instanceof Error && error.message
					? `${error.message}. Start outcome is unknown; retry the same request.`
					: 'Start outcome is unknown. Retry the same request.';
		} finally {
			this.busy = false;
			this.outcomeVersion += 1;
		}
	}

	private fail(intent: StartIntent, status: number, error: unknown) {
		const detail = apiErrorMessage(error, 'Start outcome is unknown. Retry the same request.');
		const code = apiErrorCode(error);
		const { outcome, claimId } = classifyStartFailure(status, code, detail);
		this.claimId = claimId;
		this.ownerConflict = outcome === 'retained';
		if (outcome === 'refused') {
			// A definitive refusal grants no work, so the exact request is not retained.
			this.pending = null;
			this.refusal = {
				title:
					intent.kind === 'activity'
						? `${intentLabel(intent)} was not started`
						: `PR #${intent.body.pull_number} was not enrolled`,
				detail,
				branch:
					code === 'SDD_BRANCH_EXISTS' && intent.kind === 'activity'
						? `${intent.activity}-${intent.slug}`
						: undefined,
				configuration: status === 422 && !claimId
			};
			return;
		}
		this.error =
			outcome === 'retained'
				? 'This activity has a retained owner. Inspect its Run and external work before requesting replacement work.'
				: detail;
	}

	resolvedOwner() {
		this.pending = null;
		this.error = '';
		this.claimId = '';
		this.ownerConflict = false;
		this.resolved =
			'Retained ownership reconciled. Review the intended activity before starting new work.';
	}
}
