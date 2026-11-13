<script lang="ts">
	import type { components } from '$lib/api';
	import { repositorySubjectHref } from './run-links';
	let { run }: { run: components['schemas']['PipelineRunRead'] } = $props();
	let currentUnit = $derived(
		typeof run.sdd_snapshot?.spec_dir === 'string' ? run.sdd_snapshot.spec_dir : ''
	);
	let refs = $derived(run.related_origins ?? []);
	let evidence = $derived.by(() => {
		if (run.enrollment_source) return run.enrollment_source;
		const kinds = refs.map((origin) => origin.kind);
		if (run.sdd_snapshot && Object.keys(run.sdd_snapshot).length) kinds.push('native_sdd');
		const unique = kinds.filter((kind, index) => kinds.indexOf(kind) === index);
		return unique.length > 1 ? 'multiple' : (unique[0] ?? 'unknown');
	});
	const labels = {
		work_plan: 'Work Plan',
		provider_session: 'Provider session',
		native_sdd: 'Native SDD',
		multiple: 'Multiple retained origins',
		unknown: 'Origin unknown'
	};
</script>

<div aria-label="Related origins" class="space-y-1 text-xs text-muted-foreground">
	<span>Related origin: {labels[evidence]}</span>
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
