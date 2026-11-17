<script lang="ts">
	import type { components } from '$lib/api';
	import { Button } from '$lib/components/ui/button';
	import { MessageSquare } from '@lucide/svelte';
	import RunStateBadge from '../pipeline-runs/RunStateBadge.svelte';
	import { runHref } from '../pipeline-runs/run-links';
	import { ACTIVITY_LABELS, latestRunsByActivity, runOwesOperator } from './sdd-unit';
	/**
	 * What currently holds this unit: the latest PR run per activity, so owed work is seen
	 * before a new start is offered (PRODUCT.md "Exceptions first").
	 */
	let { projectId, runs }: { projectId: string; runs: components['schemas']['PipelineRunRead'][] } =
		$props();
	let latest = $derived(latestRunsByActivity(runs));
	// One ink primary: the newest run that owes the operator; others stay secondary.
	let firstOwed = $derived(latest.find(({ run }) => runOwesOperator(run))?.run.id);
</script>

{#if latest.length}
	<ul aria-label="Unit status" class="divide-y rounded-lg border">
		{#each latest as { activity, run } (run.id)}
			<li class="flex flex-wrap items-center gap-x-2 gap-y-1.5 px-3 py-2 text-sm">
				<span class="font-medium">{activity ? ACTIVITY_LABELS[activity] : 'PR run'}</span>
				<RunStateBadge state={run.state} />
				<a
					class="inline-flex min-h-6 items-center underline-offset-4 hover:underline"
					href={runHref(run.id, projectId)}
					aria-label={`Open PR run for PR #${run.pull_number}`}>PR #{run.pull_number}</a
				>
				{#if runOwesOperator(run)}
					<Button
						class="ml-auto"
						size="sm"
						variant={run.id === firstOwed ? 'default' : 'outline'}
						href={runHref(run.id, projectId, 'decisions')}
						><MessageSquare aria-hidden="true" />Open decisions<span class="sr-only">
							for PR #{run.pull_number}</span
						></Button
					>
				{/if}
			</li>
		{/each}
	</ul>
{/if}
