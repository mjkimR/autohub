<script lang="ts">
	import type { components } from '$lib/api';
	import { repositorySubjectHref } from './run-links';
	let { run }: { run: components['schemas']['PipelineRunRead'] } = $props();
	let currentUnit = $derived(
		typeof run.sdd_snapshot?.spec_dir === 'string' ? run.sdd_snapshot.spec_dir : ''
	);
	let refs = $derived(run.related_origins ?? []);
</script>

<div aria-label="Related origins" class="space-y-1 text-xs text-muted-foreground">
	<span>Related origins</span>
	{#if !currentUnit && !refs.length}<span> · Origin unknown</span>{/if}
	{#if currentUnit}
		<p class="break-all">
			Current SDD unit <a
				class="underline underline-offset-4"
				href={repositorySubjectHref(run.project_id, { unit: currentUnit, ref: run.branch })}
				>{currentUnit}</a
			>
		</p>
	{/if}
	{#each refs as origin (`${origin.kind}-${origin.id}`)}
		<p class="break-all">
			{#if origin.kind === 'work_plan'}
				<a
					class="underline underline-offset-4"
					href={`/projects/${run.project_id}?tab=plans#work-plan-${origin.work_plan_id}`}
					>Work Plan {origin.work_plan_id}</a
				>
				·
				<a
					class="underline underline-offset-4"
					href={`/projects/${run.project_id}?tab=plans#work-item-${origin.id}`}
					>Work Item {origin.id}</a
				>
			{:else if origin.kind === 'provider_session'}
				{#if origin.url && /^https?:\/\//.test(origin.url)}
					<a class="underline underline-offset-4" href={origin.url} target="_blank" rel="noreferrer"
						>Provider session {origin.id}</a
					>
				{:else}Provider session {origin.id}{/if}
			{:else if origin.unit}
				Related SDD history <a
					class="underline underline-offset-4"
					href={repositorySubjectHref(run.project_id, { unit: origin.unit, ref: run.branch })}
					>{origin.unit}</a
				>
				{#if origin.batch_id}
					· <a
						class="underline underline-offset-4"
						href={repositorySubjectHref(run.project_id, { batch: origin.batch_id })}
						>SDD batch {origin.batch_id}</a
					>{/if}
			{/if}
		</p>
	{/each}
</div>
