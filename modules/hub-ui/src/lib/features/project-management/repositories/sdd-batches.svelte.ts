import { api, type components } from '$lib/api';
import { apiErrorMessage } from '$lib/api/errors';

export type Batch = components['schemas']['BatchRead'];
export type Preview = components['schemas']['MilestonePreview'];
export type Selection = components['schemas']['BatchSelection'];
type Create = components['schemas']['CreateBatch'];
type Control = components['schemas']['ControlBatch'];

export function selectable(member: Preview['members'][number]) {
	return (
		member.admission === 'pass' &&
		['eligible_now', 'held'].includes(member.eligibility) &&
		!Object.values(member.workflow_hold ?? {}).some(Boolean)
	);
}

export class SddBatches {
	project = '';
	rows = $state<Batch[]>([]);
	batch = $state<Batch | null>(null);
	busy = $state(false);
	error = $state('');
	staleCreate = $state(false);
	pending = $state<{
		project: string;
		create?: Create;
		control?: Control;
		batchId?: string;
	} | null>(null);
	private generation = 0;

	reset(project: string) {
        this.project = project;
        ++this.generation;
        this.rows = [];
        this.batch = null;
        this.busy = false;
        this.error = '';
        if (this.pending?.project !== project) this.pending = null;
    }

    async load(project: string) {
		this.project = project;
		const generation = ++this.generation;
		this.rows = [];
		this.busy = false;
		this.batch = null;
		this.error = '';
		if (this.pending?.project !== project) this.pending = null;
		try {
			const response = await api.GET('/api/v1/projects/{project_id}/sdd/batches', {
				params: { path: { project_id: project } }
			});
			if (generation !== this.generation) return;
			if (!response.data)
				throw new Error(apiErrorMessage(response.error, 'Unable to load SDD batches'));
			if (!Array.isArray(response.data)) throw new Error('Unable to load SDD batches');
			this.rows = response.data;
			this.batch = this.rows.find((row) => row.exclusion) ?? null;
		} catch (error) {
			if (generation === this.generation) this.error = String(error);
		}
	}

	private accept(batch: Batch) {
		if (batch.project_id !== this.project) return;
		if (this.batch?.id === batch.id && this.batch.revision > batch.revision) return;
		this.batch = batch;
		this.rows = [batch, ...this.rows.filter((row) => row.id !== batch.id)];
	}

	async refresh(id = this.batch?.id) {
		if (!id) return;
		const project = this.project;
		try {
			const response = await api.GET('/api/v1/projects/{project_id}/sdd/batches/{batch_id}', {
				params: { path: { project_id: project, batch_id: id } }
			});
			if (project !== this.project) return;
			if (!response.data)
				throw new Error(apiErrorMessage(response.error, 'Unable to refresh batch'));
			this.accept(response.data);
		} catch (error) {
			if (project === this.project) this.error = String(error);
		}
	}

	async create(preview: Preview, members: Selection[]) {
		if (this.busy || this.pending || this.staleCreate) return;
		this.pending = {
			project: this.project,
			create: {
				request_id: crypto.randomUUID(),
				ref: preview.requested_ref,
				milestone_id: String(preview.milestone.id),
				milestone_path: String(preview.milestone.path),
				expected_sha: preview.resolved_sha,
				through_development: true,
				members: structuredClone(members)
			}
		};
		await this.retry();
	}

	async control(action: Control['action']) {
		if (!this.batch || this.busy || this.pending) return;
		this.pending = {
			project: this.project,
			batchId: this.batch.id,
			control: {
				request_id: crypto.randomUUID(),
				expected_revision: this.batch.revision,
				action
			}
		};
		await this.retry();
	}

	async retry() {
		const intent = this.pending;
		if (!intent || intent.project !== this.project || this.busy) return;
		this.busy = true;
		this.error = '';
		try {
			const response = intent.create
				? await api.POST('/api/v1/projects/{project_id}/sdd/batches', {
						params: { path: { project_id: intent.project } },
						body: intent.create
					})
				: await api.POST('/api/v1/projects/{project_id}/sdd/batches/{batch_id}/controls', {
						params: { path: { project_id: intent.project, batch_id: intent.batchId! } },
						body: intent.control!
					});
			if (intent.project !== this.project) return;
			if (!response.data) {
				if (response.response.status === 409 || response.response.status === 422) {
					this.pending = null;
					if (intent.create) this.staleCreate = true;
					await this.refresh(intent.batchId);
				}
				throw new Error(apiErrorMessage(response.error, 'Outcome unknown; retry the same request'));
			}
			this.accept(response.data);
			this.pending = null;
		} catch (error) {
			if (intent.project === this.project) this.error = String(error);
		} finally {
			if (intent.project === this.project) this.busy = false;
		}
	}
}
