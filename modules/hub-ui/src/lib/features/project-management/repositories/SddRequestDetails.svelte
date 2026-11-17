<script lang="ts">
	import WrapAtSeparators from '../pipeline-runs/WrapAtSeparators.svelte';
	import { intentLabel, intentUnit, type StartIntent } from './sdd-starts.svelte';
	import { effortLabel } from './sdd-unit';
	/** Internal identities of the original request, kept out of the way until they are needed. */
	let {
		intent,
		repository = '',
		claimId = ''
	}: { intent: StartIntent | null; repository?: string; claimId?: string } = $props();
	let rows = $derived.by(() => {
		const list: [string, string][] = [];
		if (repository) list.push(['Repository', repository]);
		if (intent) {
			list.push(['Work', intentLabel(intent)], ['Unit', intentUnit(intent)]);
			if (intent.kind === 'activity') list.push(['Base', intent.body.base_branch]);
			else list.push(['Pull request', `#${intent.body.pull_number}`]);
			list.push(
				['Effort', effortLabel(intent.body.activity_effort)],
				['Catalog', intent.body.catalog || 'Project default'],
				['Project', intent.project]
			);
			if (intent.kind === 'activity') list.push(['Request', intent.body.request_id]);
		}
		if (claimId) list.push(['Claim', claimId]);
		return list;
	});
</script>

{#if rows.length}
	<details class="text-xs">
		<summary class="inline-flex min-h-6 cursor-pointer items-center text-muted-foreground"
			>Request details</summary
		>
		<dl class="mt-2 space-y-1">
			{#each rows as [label, value] (label)}
				<div class="flex gap-3">
					<dt class="w-20 shrink-0 text-muted-foreground">{label}</dt>
					<dd class="min-w-0 font-mono break-words"><WrapAtSeparators text={value} /></dd>
				</div>
			{/each}
		</dl>
	</details>
{/if}
