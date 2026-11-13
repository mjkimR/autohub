import { api, type components } from '$lib/api';
import { apiErrorMessage } from '$lib/api/errors';
import { responseData } from '$lib/api/pagination';
export type Batch = components['schemas']['BatchRead'];

/** Historical subjects only. Detail selection and once-per-project list loading are independent. */
export class SddBatches {
	project = '';
	rows = $state<Batch[]>([]);
	batch = $state<Batch | null>(null);
	requestedId = $state('');
	busy = $state(false);
	listBusy = $state(false);
	loaded = $state(false);
	error = $state('');
	listError = $state('');
	private generation = 0;
	private listGeneration = 0;
	reset(project: string) {
		if (project === this.project) return;
		this.project = project;
		++this.generation;
		++this.listGeneration;
		this.rows = [];
		this.batch = null;
		this.requestedId = '';
		this.error = '';
		this.listError = '';
		this.busy = this.listBusy = this.loaded = false;
	}
	clear() {
		++this.generation;
		this.requestedId = '';
		this.batch = null;
		this.error = '';
		this.busy = false;
	}
	async load(project: string) {
		this.reset(project);
		if (this.loaded || this.listBusy) return;
		const generation = ++this.listGeneration;
		this.listBusy = true;
		this.listError = '';
		try {
			const rows = responseData(
				await api.GET('/api/v1/projects/{project_id}/sdd/batches', {
					params: { path: { project_id: project } }
				}),
				'Unable to load retained batches'
			);
			if (generation !== this.listGeneration || project !== this.project) return;
			this.rows = this.batch
				? [this.batch, ...rows.filter((row) => row.id !== this.batch?.id)]
				: rows;
			this.loaded = true;
		} catch (e) {
			if (generation === this.listGeneration && project === this.project)
				this.listError = e instanceof Error ? e.message : 'Unable to load retained batches';
		} finally {
			if (generation === this.listGeneration && project === this.project) this.listBusy = false;
		}
	}
	async refresh(id = this.requestedId || this.batch?.id) {
		if (!id) return;
		const project = this.project,
			generation = ++this.generation;
		this.requestedId = id;
		this.batch = null;
		this.busy = true;
		this.error = '';
		try {
			const response = await api.GET('/api/v1/projects/{project_id}/sdd/batches/{batch_id}', {
				params: { path: { project_id: project, batch_id: id } }
			});
			if (generation !== this.generation || project !== this.project) return;
			if (response.error || !response.data)
				throw new Error(apiErrorMessage(response.error, 'Batch unavailable'));
			const row = response.data;
			if (row.id !== id || row.project_id !== project)
				throw new Error('Batch unavailable: the returned subject does not match this address');
			this.batch = row;
			this.rows = [row, ...this.rows.filter((known) => known.id !== row.id)];
		} catch (e) {
			if (generation === this.generation && project === this.project)
				this.error = e instanceof Error ? e.message : 'Unable to load this retained batch';
		} finally {
			if (generation === this.generation && project === this.project) this.busy = false;
		}
	}
}
