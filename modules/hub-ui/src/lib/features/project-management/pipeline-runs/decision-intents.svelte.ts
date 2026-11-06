import { api, type components } from '$lib/api';
import { responseData } from '$lib/api/pagination';
import { session } from '$lib/stores/session.svelte';

type Resume = components['schemas']['ResumeRunRequest'];
type Operation = 'question' | 'answer' | 'resume';
type Intent = {
	operation: Operation;
	requestId: string;
	questionId?: string;
	body:
		Resume | { request_id: string; expected_revision: number; answer?: string; question?: string };
	head: string;
	generation: number;
	acknowledged: boolean;
	rejected?: boolean;
};
type Outcome = components['schemas']['DecisionOutcome'];
export function decisionBasis(run: components['schemas']['PipelineRunRead']) {
	const p = run.sdd_progress || {};
	return JSON.stringify([
		p.head_sha || run.pull_snapshot?.head_sha || '',
		p.approval,
		p.hold,
		run.project_id,
		run.sdd_snapshot
	]);
}
const reviews: Record<string, DecisionIntent> = {};
export function decisionIntent(runId: string, recovery = false) {
	const key = `${session.generation}:${runId}:${recovery}`;
	for (const [id, value] of Object.entries(reviews))
		if (value.generation !== session.generation) delete reviews[id];
	if (!reviews[key]) reviews[key] = new DecisionIntent(runId, recovery);
	return reviews[key];
}
export class DecisionIntent {
	generation = session.generation;
	intent = $state<Intent | null>(null);
	subject = $state<{ operation: Operation; requestId: string } | null>(null);
	outcome = $state<Outcome | null>(null);
	error = $state('');
	busy = $state(false);
	constructor(
		readonly runId: string,
		readonly recovery = false
	) {}
	get competingUnresolved() {
		return Object.values(reviews).some(
			(other) =>
				other !== this &&
				other.runId === this.runId &&
				other.validSession &&
				other.unresolved &&
				!(
					this.recovery &&
					!other.recovery &&
					['accept_plan', 'reject_plan'].includes((other.intent?.body as Resume)?.decision || '')
				)
		);
	}
	get unresolved() {
		return !!this.intent && !this.intent.acknowledged;
	}
	get validSession() {
		return this.generation === session.generation;
	}
	get displayingIntent() {
		return (
			!!this.intent &&
			this.subject?.operation === this.intent.operation &&
			this.subject.requestId === this.intent.requestId
		);
	}
	releaseRejection() {
		if (this.intent?.rejected) {
			this.intent = null;
			this.error = '';
		}
	}
	async submit(operation: Operation, body: Intent['body'], head: string, questionId?: string) {
		if (!this.validSession || this.unresolved || this.competingUnresolved)
			throw new Error('Check the original outcome before another submission');
		this.intent = {
			operation,
			requestId: body.request_id,
			body: structuredClone(body),
			head,
			questionId,
			generation: this.generation,
			acknowledged: false
		};
		this.subject = { operation, requestId: body.request_id };
		this.outcome = null;
		await this.retry(head, true);
	}
	async retry(head: string, initial = false) {
		const i = this.intent;
		if (
			!i ||
			i.rejected ||
			!this.validSession ||
			this.busy ||
			this.competingUnresolved ||
			(!initial && i.head !== head)
		)
			return;
		this.busy = true;
		this.error = '';
		try {
			const result =
				i.operation === 'resume'
					? await api.POST('/api/v1/pipeline-runs/{run_id}/resume', {
							params: { path: { run_id: this.runId } },
							body: i.body as Resume
						})
					: i.operation === 'answer'
						? await api.POST('/api/v1/pipeline-runs/{run_id}/questions/{question_id}/answers', {
								params: { path: { run_id: this.runId, question_id: i.questionId! } },
								body: i.body as components['schemas']['AnswerWrite']
							})
						: await api.POST('/api/v1/pipeline-runs/{run_id}/questions', {
								params: { path: { run_id: this.runId } },
								body: i.body as components['schemas']['QuestionWrite']
							});
			if (!this.validSession) return;
			// Only FastAPI's structured request validation proves failure before owner execution.
			// Owner 4xx may follow a prepared/pushed candidate and stays uncertain.
			if (
				result.response?.status === 422 &&
				result.error &&
				typeof result.error === 'object' &&
				'detail' in result.error &&
				Array.isArray(result.error.detail)
			)
				i.rejected = true;
			responseData<unknown>(result, 'Request outcome unknown');
			i.acknowledged = true;
			await this.check(i.operation, i.requestId);
		} catch (e) {
			this.error = i.rejected
				? 'Request rejected. Review current context before correcting input.'
				: i.acknowledged
					? 'Recorded. Refresh failed; retry read.'
					: `Outcome unknown. ${e instanceof Error ? e.message : 'Check outcome'}`;
			if (!i.acknowledged) throw e;
		} finally {
			this.busy = false;
		}
	}
	async check(operation = this.subject?.operation, requestId = this.subject?.requestId) {
		if (!operation || !requestId || !this.validSession) return;
		this.subject = { operation, requestId };
		this.error = '';
		// Evidence from another subject must never remain under this identity during an error.
		if (this.outcome?.operation !== operation || this.outcome.request_id !== requestId)
			this.outcome = null;
		try {
			const data = responseData(
				await api.GET('/api/v1/pipeline-runs/{run_id}/decision-outcomes/{request_id}', {
					params: { path: { run_id: this.runId, request_id: requestId }, query: { operation } }
				}),
				'Unable to check outcome'
			);
			if (
				this.validSession &&
				this.subject.operation === operation &&
				this.subject.requestId === requestId
			)
				this.outcome = data;
		} catch (e) {
			this.error = 'Outcome read failed. Prior recorded result is retained.';
			throw e;
		}
	}
}
