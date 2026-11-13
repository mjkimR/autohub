<script lang="ts">
	import type { components } from '$lib/api';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import SddReports from './SddReports.svelte';
	let { run }: { run: components['schemas']['PipelineRunRead'] } = $props();
	let snapshot = $derived(run.sdd_snapshot || {});
	let legacy = $derived(snapshot.execution_version !== 2);
	let unit = $derived(String(snapshot.spec_dir || ''));
	let head = $derived(
		String((legacy ? run.sdd_progress?.head_sha : null) || run.pull_snapshot?.head_sha || '')
	);
	let evidenceUrl = $derived(
		unit && head ? `${run.pull_url.split('/pull/')[0]}/tree/${head}/${unit}` : null
	);
</script>

<section class="space-y-3 rounded-xl border bg-card p-4" aria-label="Repository activity context">
	<div class="flex flex-wrap items-center gap-2">
		<h3 class="text-sm font-semibold">Repository activity</h3>
		<Badge variant="outline"
			>{legacy
				? 'Retired · read only'
				: String(
						snapshot.activity_kind || (snapshot.handoff_pending ? 'Development' : 'Repository work')
					)}</Badge
		>
	</div>
	{#if legacy}
		<p class="text-sm text-muted-foreground">
			Native SDD workflow control has been retired. This evidence is historical and cannot resume or
			approve work. Inspect any external agent and PR activity before registering replacement work.
		</p>
	{:else}
		<p class="text-sm text-muted-foreground">
			The agent owns repository setup and workflow execution. Use this Run's ordinary questions and
			controls; GitHub checks and project merge policy govern delivery.
		</p>
	{/if}
	{#if unit}<p class="text-xs break-all">Unit: <code>{unit}</code></p>{/if}
	{#if snapshot.activity_effort}<p class="text-xs text-muted-foreground">
			Activity effort: {String(snapshot.activity_effort)}
		</p>{/if}
	{#if evidenceUrl}<Button
			size="sm"
			variant="link"
			href={evidenceUrl}
			target="_blank"
			rel="noreferrer">Open repository evidence</Button
		>{/if}
	{#if legacy && run.sdd_progress}
		<details class="text-xs">
			<summary class="cursor-pointer text-muted-foreground"
				>Retained native execution evidence</summary
			>
			<div class="mt-3 space-y-3">
				<SddReports reports={run.sdd_progress.reports} {evidenceUrl} />
				<pre class="overflow-auto break-all whitespace-pre-wrap">{JSON.stringify(
						run.sdd_progress,
						null,
						2
					)}</pre>
			</div>
		</details>
	{/if}
</section>
