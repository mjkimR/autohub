<script lang="ts">
	import { GitPullRequest, Play, History } from '@lucide/svelte';
	import SddProposals from './SddProposals.svelte';
	import SddExecution from './SddExecution.svelte';
	import SddRunLinks from './SddRunLinks.svelte';
	import { sddStarts } from './sdd-starts.svelte';
	import { unitDirectory } from './repository-selection.svelte';
	let {
		projectId,
		repository,
		path,
		branch
	}: { projectId: string; repository: string; path: string; branch: string } = $props();
	const candidate = $derived(
		path.match(/^(specs\/\d{4}-\d{2}\/[^/]+|docs\/proposals\/PROP-[^/]+)\//)?.[1] || ''
	);
	const unit = $derived(unitDirectory.test(candidate) ? candidate : '');
	const starts = $derived(sddStarts(projectId));
</script>

{#if unit}
	<section aria-label="Selected SDD unit" class="space-y-4 rounded-xl border bg-card p-4">
		<div class="space-y-1">
			<h3 class="flex items-center gap-2 text-sm font-semibold">
				<Play class="size-4 text-muted-foreground" aria-hidden="true" />Work on this unit
			</h3>
			<p class="font-mono text-xs break-all text-muted-foreground">{unit}</p>
		</div>
		{#key `${unit}:${branch}`}
			{#if unit.startsWith('docs/proposals/')}<SddProposals {projectId} {unit} {branch} />{/if}
			<details class="border-t pt-3">
				<summary class="flex cursor-pointer items-center gap-2 text-sm font-medium"
					><GitPullRequest class="size-4 text-muted-foreground" aria-hidden="true" />Enroll an
					existing PR</summary
				>
				<div class="pt-3">
					<SddExecution {projectId} selectedSpec={unit} {repository} contextual />
				</div>
			</details>
		{/key}
		<div class="space-y-2 border-t pt-3">
			<h4 class="flex items-center gap-2 text-sm font-medium">
				<History class="size-4 text-muted-foreground" aria-hidden="true" />Execution history
			</h4>
			<SddRunLinks {projectId} {repository} specDir={unit} refresh={starts.runId} />
		</div>
	</section>
{/if}
