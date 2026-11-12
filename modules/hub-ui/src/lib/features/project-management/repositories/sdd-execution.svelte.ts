import { api, type components } from '$lib/api';
import { apiErrorMessage } from '$lib/api/errors';

type Readiness = components['schemas']['SddReadiness'];

export class SddExecutionState {
	spec = $state('');
	pull = $state<number>(1);
	effort = $state<'low' | 'medium' | 'high'>('medium');
	busy = $state(false);
	message = $state('');
	error = $state('');
	private resultKey = $state('');
	private inspection = $state<Readiness | null>(null);
	runtime = $state('');
	runtimeError = $state('');
	runId = $state('');
	startedKey = $state('');
	private generation = 0;

	constructor(private projectId: () => string) {}

	key() {
		return JSON.stringify([this.projectId(), this.spec, this.pull]);
	}

	get readiness() {
		return this.resultKey === this.key() ? this.inspection : null;
	}

	get visibleError() {
		return this.resultKey === this.key() ? this.error : '';
	}

	get visibleMessage() {
		return this.resultKey === this.key() ? this.message : '';
	}

	get canStart() {
		return !this.busy && this.readiness?.ready && !(this.runId && this.startedKey === this.key());
	}

	async checkRuntime() {
		const project = this.projectId();
		this.busy = true;
		this.runtime = '';
		this.runtimeError = '';
		try {
			const result = await api.GET('/api/v1/projects/{project_id}/sdd/runtime', {
				params: { path: { project_id: project } }
			});
			if (project !== this.projectId()) return;
			if (result.error)
				throw new Error(apiErrorMessage(result.error, 'Unable to check the runtime'));
			const status = result.data;
			const revision = status.revisions?.['devkit-spec']?.slice(0, 12);
			const summary = `Runtime ${status.isolation ?? 'without a sandbox'}: ${status.ok ? 'ok' : 'unavailable'}${revision ? ` · devkit-spec ${revision}` : ''}`;
			if (status.ok)
				this.runtime = `${summary} · profile ${status.profile ?? 'default'} · bundles: ${(status.bundles ?? []).join(', ') || 'unknown'}`;
			else this.runtimeError = `${summary}. ${status.detail ?? ''}`.trim();
		} catch (error) {
			if (project === this.projectId())
				this.runtimeError = error instanceof Error ? error.message : 'Runtime check failed';
		} finally {
			this.busy = false;
		}
	}

	async inspect() {
		const requestedKey = this.key();
		const generation = ++this.generation;
		this.busy = true;
		this.error = '';
		this.message = '';
		this.inspection = null;
		this.resultKey = requestedKey;
		try {
			const result = await api.POST('/api/v1/projects/{project_id}/sdd/readiness', {
				params: { path: { project_id: this.projectId() } },
				body: { spec_dir: this.spec, pull_number: this.pull }
			});
			if (generation !== this.generation || requestedKey !== this.key()) return;
			if (result.error) throw new Error(apiErrorMessage(result.error, 'Unable to inspect spec'));
			this.inspection = result.data;
			if (!result.data?.ready) this.error = result.data?.reason || 'Project needs setup';
		} catch (error) {
			if (generation === this.generation && requestedKey === this.key())
				this.error = error instanceof Error ? error.message : 'Inspection failed';
		} finally {
			if (generation === this.generation) this.busy = false;
		}
	}

	async start() {
		if (!this.canStart) return;
		const requestedKey = this.key();
		this.busy = true;
		this.error = '';
		this.resultKey = requestedKey;
		try {
			const result = await api.POST('/api/v1/projects/{project_id}/runs', {
				params: { path: { project_id: this.projectId() } },
				body: {
					spec_dir: this.spec,
					pull_number: this.pull,
					implemented: false,
					handoff: false,
					activity_effort: this.effort
				}
			});
			if (result.error)
				throw new Error(apiErrorMessage(result.error, 'Unable to start spec execution'));
			this.runId = result.data?.id || '';
			this.startedKey = requestedKey;
			if (requestedKey === this.key())
				this.message = 'Execution registered. Follow its stages and decisions in Pipeline Runs.';
		} catch (error) {
			if (requestedKey === this.key())
				this.error = error instanceof Error ? error.message : 'Could not start execution';
		} finally {
			this.busy = false;
		}
	}
}
