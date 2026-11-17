import { sddStarts } from './sdd-starts.svelte';

export class SddExecutionState {
	spec = $state('');
	pull = $state<number | undefined>(undefined);
	/** Empty follows the repository recommendation, as the activity start form does. */
	effort = $state<'' | 'low' | 'medium' | 'high'>('');
	constructor(private projectId: () => string) {}
	get starts() {
		return sddStarts(this.projectId());
	}
	get canStart() {
		return (
			!!this.spec &&
			Number.isInteger(this.pull) &&
			(this.pull ?? 0) > 0 &&
			!this.starts.busy &&
			!this.starts.pending
		);
	}
	async start() {
		if (!this.canStart) return;
		await this.starts.enroll(this.projectId(), {
			spec_dir: this.spec,
			pull_number: this.pull!,
			implemented: false,
			handoff: false,
			...(this.effort ? { activity_effort: this.effort } : {})
		});
	}
}
