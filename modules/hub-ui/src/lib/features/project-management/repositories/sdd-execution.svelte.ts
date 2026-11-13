import { sddStarts } from './sdd-starts.svelte';

export class SddExecutionState {
	spec = $state('');
	pull = $state(1);
	effort = $state<'low' | 'medium' | 'high'>('medium');
	constructor(private projectId: () => string) {}
	get starts() {
		return sddStarts(this.projectId());
	}
	get canStart() {
		return !!this.spec && this.pull > 0 && !this.starts.busy && !this.starts.pending;
	}
	async start() {
		if (!this.canStart) return;
		await this.starts.enroll(this.projectId(), {
			spec_dir: this.spec,
			pull_number: this.pull,
			implemented: false,
			handoff: false,
			activity_effort: this.effort
		});
	}
}
