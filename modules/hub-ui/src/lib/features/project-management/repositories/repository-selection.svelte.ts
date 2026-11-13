import { repositoryDataSource } from './data-source';
import type { RepoInfo } from './types';

export const unitDirectory =
	/^(specs\/[0-9]{4}-[0-9]{2}\/[a-zA-Z0-9_-]+|docs\/proposals\/PROP-[a-z0-9][a-z0-9_-]*)$/;

/** A URL is a browse request. Only an existing recognized unit reaches activity selection. */
export class RepositorySelection {
	info = $state<RepoInfo | null>(null);
	ref = $state('');
	unit = $state('');
	requestedUnit = $state('');
	status = $state<'loading' | 'ready' | 'unavailable' | 'error'>('loading');
	error = $state('');
	missingRef = $state(false);
	private generation = 0;
	private controller: AbortController | null = null;

	async select(project: string, isSdd: boolean, unit: string, ref: string) {
		const generation = ++this.generation;
		this.controller?.abort();
		this.controller = new AbortController();
		const signal = this.controller.signal;
		this.info = null;
		this.ref = ref;
		this.unit = '';
		this.requestedUnit = unit;
		this.status = 'loading';
		this.error = '';
		this.missingRef = false;
		if (unit && (!isSdd || !unitDirectory.test(unit))) {
			this.status = 'unavailable';
			this.error = !isSdd
				? 'This project does not support SDD unit selection.'
				: 'The requested unit directory is invalid.';
			return;
		}
		try {
			const source = repositoryDataSource(project);
			const info = await source.info(signal);
			if (generation !== this.generation) return;
			this.info = info;
			this.ref = ref || info.default_branch;
			if (ref && info.branches_complete !== false && !(info.branches ?? []).includes(ref)) {
				this.missingRef = true;
				this.status = 'unavailable';
				this.error = `Repository branch ${ref} is unavailable.`;
				return;
			}
			if (unit) {
				await source.blob(
					`${unit}/${unit.startsWith('specs/') ? 'spec.md' : 'proposal.md'}`,
					this.ref,
					signal
				);
				if (generation !== this.generation) return;
				this.unit = unit;
			}
			this.status = 'ready';
		} catch (error) {
			if (generation !== this.generation) return;
			this.status = 'error';
			this.error =
				error instanceof Error ? error.message : 'The requested repository subject is unavailable.';
		}
	}

	destroy() {
		++this.generation;
		this.controller?.abort();
	}
}
