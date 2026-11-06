import { api, type components } from '$lib/api';
import { responseData } from '$lib/api/pagination';
import { session } from '$lib/stores/session.svelte';

type Resume = components['schemas']['ResumeRunRequest'];
type Intent = {
	operation: 'question' | 'answer' | 'resume';
	requestId: string;
	questionId?: string;
	body:
		Resume | { request_id: string; expected_revision: number; answer?: string; question?: string };
	head: string;
	generation: number;
	acknowledged: boolean;
};
type Outcome = components['schemas']['DecisionOutcome'];
export function decisionBasis(run: components['schemas']['PipelineRunRead']) {
	const progress = run.sdd_progress || {};
	return JSON.stringify([
		progress.head_sha || run.pull_snapshot?.head_sha || '',
		progress.approval,
		progress.hold,
		run.project_id,
		run.sdd_snapshot
	]);
}
const reviews = new Map<string, DecisionIntent>();
export function decisionIntent(runId: string) {
	const key = `${session.generation}:${runId}`;
	for (const [id, value] of reviews)
		if (value.generation !== session.generation) reviews.delete(id);
	if (!reviews.has(key)) reviews.set(key, new DecisionIntent(runId));
	return reviews.get(key)!;
}
export class DecisionIntent {
	generation = session.generation;
	intent = $state<Intent | null>(null);
	outcome = $state<Outcome | null>(null);
	error = $state('');
	busy = $state(false);
	constructor(readonly runId: string) {}
	get unresolved() {
		return !!this.intent && !this.intent.acknowledged;
	}
	get validSession() {
		return this.generation === session.generation;
	}
	async submit(
		operation: Intent['operation'],
		body: Intent['body'],
		head: string,
		questionId?: string
	) {
		if (!this.validSession || this.unresolved)
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
		this.outcome = null;
		await this.retry(head, true);
	}
	async retry(head: string, initial = false) {
		const i = this.intent;
		if (!i || !this.validSession || this.busy || (!initial && i.head !== head)) return;
		this.busy = true;
		this.error = '';
		try {
			if (i.operation === 'resume')
				responseData(
					await api.POST('/api/v1/pipeline-runs/{run_id}/resume', {
						params: { path: { run_id: this.runId } },
						body: i.body as Resume
					}),
					'Request outcome unknown'
				);
			else if (i.operation === 'answer')
				responseData(
					await api.POST('/api/v1/pipeline-runs/{run_id}/questions/{question_id}/answers', {
						params: { path: { run_id: this.runId, question_id: i.questionId! } },
						body: i.body as components['schemas']['AnswerWrite']
					}),
					'Request outcome unknown'
				);
			else
				responseData(
					await api.POST('/api/v1/pipeline-runs/{run_id}/questions', {
						params: { path: { run_id: this.runId } },
						body: i.body as components['schemas']['QuestionWrite']
					}),
					'Request outcome unknown'
				);
			if (!this.validSession) return;
			i.acknowledged = true;
			await this.check();
		} catch (e) {
			this.error = i.acknowledged
				? 'Recorded. Refresh failed; retry read.'
				: `Outcome unknown. ${e instanceof Error ? e.message : 'Check outcome'}`;
			if (!i.acknowledged) throw e;
		} finally {
			this.busy = false;
		}
	}
	async check(operation = this.intent?.operation, requestId = this.intent?.requestId) {
		if (!operation || !requestId || !this.validSession) return;
		this.error = '';
		try {
			this.outcome = responseData(
				await api.GET('/api/v1/pipeline-runs/{run_id}/decision-outcomes/{request_id}', {
					params: { path: { run_id: this.runId, request_id: requestId }, query: { operation } }
				}),
				'Unable to check outcome'
			);
		} catch (e) {
			this.error = 'Outcome read failed. Prior recorded result is retained.';
			throw e;
		}
	}
}
