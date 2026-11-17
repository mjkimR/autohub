<script lang="ts">
	import WrapAtSeparators from '../pipeline-runs/WrapAtSeparators.svelte';
	import type { components } from '$lib/api';
	import { GitPullRequest, Play, History } from '@lucide/svelte';
	import SddProposals from './SddProposals.svelte';
	import SddExecution from './SddExecution.svelte';
	import SddRunLinks from './SddRunLinks.svelte';
	import SddUnitOutcome from './SddUnitOutcome.svelte';
	import SddUnitStatus from './SddUnitStatus.svelte';
	import { sddStarts } from './sdd-starts.svelte';
	import { activeRunsByActivity, unitFromPath } from './sdd-unit';
	let {
		projectId,
		repository,
		path,
		branch
	}: { projectId: string; repository: string; path: string; branch: string } = $props();
	const unit = $derived(unitFromPath(path));
	const proposal = $derived(unit.startsWith('docs/proposals/'));
	const starts = $derived(sddStarts(projectId));
	let runs = $state<components['schemas']['PipelineRunRead'][]>([]);
	const active = $derived(activeRunsByActivity(runs));
</script>

{#if unit}
	<section
		id="sdd-unit-panel"
		tabindex="-1"
		aria-label="Selected SDD unit"
		class="scroll-mt-6 space-y-4 rounded-xl border bg-card p-4"
	>
		<div class="space-y-1">
			<h3 class="flex items-center gap-2 text-sm font-semibold">
				<Play class="size-4 text-muted-foreground" aria-hidden="true" />Work on this unit
			</h3>
			<p class="font-mono text-xs break-words text-muted-foreground">
				<WrapAtSeparators text={unit} />
			</p>
		</div>
		<SddUnitStatus {projectId} {runs} />
		{#key `${unit}:${branch}`}
			{#if proposal}<SddProposals {projectId} {unit} {branch} {active} />
				<SddUnitOutcome {projectId} {unit} {repository} />{/if}
			<details class="border-t pt-3">
				<summary class="flex cursor-pointer items-center gap-2 text-sm font-medium"
					><GitPullRequest class="size-4 text-muted-foreground" aria-hidden="true" />Enroll an
					existing PR</summary
				>
				<div class="pt-3">
					<SddExecution {projectId} selectedSpec={unit} {repository} contextual />
				</div>
			</details>
			{#if !proposal}<SddUnitOutcome {projectId} {unit} {repository} />{/if}
		{/key}
		<div class="space-y-2 border-t pt-3">
			<h4 class="flex items-center gap-2 text-sm font-medium">
				<History class="size-4 text-muted-foreground" aria-hidden="true" />PR runs for this unit
			</h4>
			<SddRunLinks {projectId} {repository} specDir={unit} refresh={starts.runId} bind:runs />
		</div>
	</section>
{/if}
