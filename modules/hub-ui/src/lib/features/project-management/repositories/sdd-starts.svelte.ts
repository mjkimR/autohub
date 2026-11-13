import { api, type components } from '$lib/api';
import { apiErrorMessage } from '$lib/api/errors';
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
	busy = $state(false);
	error = $state('');
	message = $state('');
	runId = $state('');
	claimId = $state('');
	ownerConflict = $state(false);

	async activity(project: string, slug: string, activity: 'plan' | 'dev', body: ActivityRequest) {
		if (this.pending || this.busy) return;
		this.runId = '';
		this.error = this.message = this.claimId = '';
		this.ownerConflict = false;
		this.lastKind = 'activity';
		this.pending = { kind: 'activity', project, slug, activity, body: { ...body } };
		await this.retry();
	}

	async enroll(project: string, body: Enrollment) {
		if (this.pending || this.busy) return;
		this.runId = '';
		this.error = this.message = this.claimId = '';
		this.ownerConflict = false;
		this.lastKind = 'enroll';
		this.pending = { kind: 'enroll', project, body: { ...body } };
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
				const message = apiErrorMessage(
					response.error,
					'Start outcome is unknown. Retry the same request.'
				);
				this.ownerConflict = response.response.status === 409 || response.response.status === 410;
				this.claimId = message.match(/claims\/([0-9a-f-]{36})/i)?.[1] ?? '';
				// A definitive input/auth refusal grants no work. Unknown publication and retained
				// ownership keep the exact original intent, even if another document is selected.
				if (
					response.response.status >= 400 &&
					response.response.status < 500 &&
					!this.ownerConflict
				)
					this.pending = null;
				throw new Error(
					this.claimId
						? 'This activity has a retained owner. Inspect its Run and external work before requesting replacement work.'
						: message
				);
			}
			this.runId = response.data.id;
			this.message =
				'Work registered. Follow the PR run; repository setup and workflow belong to its agent.';
			this.pending = null;
			this.ownerConflict = false;
			this.claimId = '';
		} catch (error) {
			this.error =
				error instanceof Error
					? error.message
					: 'Start outcome is unknown. Retry the same request.';
		} finally {
			this.busy = false;
		}
	}

	resolvedOwner() {
		this.pending = null;
		this.error = '';
		this.claimId = '';
		this.ownerConflict = false;
		this.message =
			'Retained ownership reconciled. Review the intended activity before starting new work.';
	}
}
