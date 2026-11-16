<script lang="ts">
	import type { components } from '$lib/api';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	let { run }: { run: components['schemas']['PipelineRunRead'] } = $props();
	let snapshot = $derived(run.sdd_snapshot || {});
	let unit = $derived(String(snapshot.spec_dir || ''));
	let head = $derived(String(run.pull_snapshot?.head_sha || ''));
	let evidenceUrl = $derived(
		unit && head ? `${run.pull_url.split('/pull/')[0]}/tree/${head}/${unit}` : null
	);
</script>

<section class="space-y-3 rounded-xl border bg-card p-4" aria-label="Repository activity context">
	<div class="flex flex-wrap items-center gap-2">
		<h3 class="text-sm font-semibold">Repository activity</h3>
		<Badge variant="outline"
			>{String(
				snapshot.activity_kind || (snapshot.handoff_pending ? 'Development' : 'Repository work')
			)}</Badge
		>
	</div>
	<p class="text-sm text-muted-foreground">
		The agent owns repository setup and workflow execution. Use this Run's ordinary questions and
		controls; GitHub checks and project merge policy govern delivery.
	</p>
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
</section>
