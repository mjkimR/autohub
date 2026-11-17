<script lang="ts">
	import type { components } from '$lib/api';
	import { Check, Circle, CircleDot, ExternalLink } from '@lucide/svelte';
	import { gateSteps, sddUnit } from './sdd-gate';
	/**
	 * Evidence and progress for an SDD activity question, shown inside its question card: the
	 * head the question is bound to, the unit and PR changes at that head, and the gate's path.
	 * Hub does not interpret the repository workflow; the agent owns setup and stages.
	 */
	let {
		run,
		question
	}: {
		run: components['schemas']['PipelineRunRead'];
		question: components['schemas']['QuestionRead'];
	} = $props();
	let unit = $derived(sddUnit(run));
	let head = $derived(question.head_sha || String(run.pull_snapshot?.head_sha || ''));
	let repoUrl = $derived(run.pull_url ? run.pull_url.split('/pull/')[0] : '');
	let unitUrl = $derived(unit && head && repoUrl ? `${repoUrl}/tree/${head}/${unit}` : '');
	let changesUrl = $derived(run.pull_url ? `${run.pull_url}/files` : '');
	let steps = $derived(gateSteps(run, question));
	const STATUS_TEXT = { done: 'done', current: 'current step', next: 'not yet' } as const;
</script>

<section class="space-y-3 rounded-lg border p-3 text-sm" aria-label="Gate evidence and progress">
	<div class="flex flex-wrap items-center gap-x-3 gap-y-1">
		{#if head}<span class="text-xs text-muted-foreground"
				>Evidence at head <code class="text-foreground">{head.slice(0, 8)}</code></span
			>{/if}
		{#if unitUrl}<a
				class="inline-flex min-h-6 items-center gap-1 underline underline-offset-4"
				href={unitUrl}
				target="_blank"
				rel="noreferrer"
				>Open unit at this head<ExternalLink aria-hidden="true" class="size-3.5" /><span
					class="sr-only">(opens in a new tab)</span
				></a
			>{/if}
		{#if changesUrl}<a
				class="inline-flex min-h-6 items-center gap-1 underline underline-offset-4"
				href={changesUrl}
				target="_blank"
				rel="noreferrer"
				>View PR changes<ExternalLink aria-hidden="true" class="size-3.5" /><span class="sr-only"
					>(opens in a new tab)</span
				></a
			>{/if}
	</div>
	<ol aria-label="Gate progress" class="flex flex-wrap gap-x-4 gap-y-1 text-xs">
		{#each steps as step (step.label)}
			<li
				class={[
					'flex items-center gap-1.5',
					step.status === 'current' ? 'font-medium text-foreground' : 'text-muted-foreground'
				]}
			>
				{#if step.status === 'done'}<Check aria-hidden="true" class="size-3.5" />
				{:else if step.status === 'current'}<CircleDot aria-hidden="true" class="size-3.5" />
				{:else}<Circle aria-hidden="true" class="size-3.5" />{/if}
				{step.label}<span class="sr-only">({STATUS_TEXT[step.status]})</span>
			</li>
		{/each}
	</ol>
	<p class="text-xs text-muted-foreground">
		The agent leaves the PR as a Draft. Once it has applied your answer, mark the PR Ready in GitHub
		to continue delivery.
	</p>
</section>
