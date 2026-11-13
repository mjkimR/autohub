import { api, type components } from '$lib/api';
import { responseData } from '$lib/api/pagination';
export type Batch = components['schemas']['BatchRead'];

/** Historical native selections; this store deliberately exposes no execution mutation. */
export class SddBatches {
	project = '';
	rows = $state<Batch[]>([]);
	batch = $state<Batch | null>(null);
	busy = $state(false);
	error = $state('');
	private generation = 0;
	reset(project: string) {
		this.project = project;
		++this.generation;
		this.rows = [];
		this.batch = null;
		this.error = '';
		this.busy = false;
	}
	async load(project: string) {
		if (project !== this.project) this.reset(project);
		const generation = ++this.generation;
		this.busy = true;
		this.error = '';
		try {
			const rows = responseData(
				await api.GET('/api/v1/projects/{project_id}/sdd/batches', {
					params: { path: { project_id: project } }
				}),
				'Unable to load retained batches'
			);
			if (generation !== this.generation) return;
			this.rows = rows;
			if (this.batch && !rows.some((row) => row.id === this.batch?.id))
				this.rows = [this.batch, ...rows];
		} catch (e) {
			if (generation === this.generation)
				this.error = e instanceof Error ? e.message : 'Unable to load retained batches';
		} finally {
			if (generation === this.generation) this.busy = false;
		}
	}
	async refresh(id = this.batch?.id) {
		if (!id) return;
		const project = this.project,
			generation = ++this.generation;
		this.busy = true;
		this.error = '';
		try {
			const row = responseData(
				await api.GET('/api/v1/projects/{project_id}/sdd/batches/{batch_id}', {
					params: { path: { project_id: project, batch_id: id } }
				}),
				'Unable to load this retained batch'
			);
			if (generation !== this.generation || project !== this.project) return;
			this.batch = row;
			this.rows = [row, ...this.rows.filter((known) => known.id !== row.id)];
		} catch (e) {
			if (generation === this.generation)
				this.error = e instanceof Error ? e.message : 'Unable to load this retained batch';
		} finally {
			if (generation === this.generation) this.busy = false;
		}
	}
}
