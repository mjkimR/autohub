<script lang="ts">
	import type { components } from '$lib/api';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { displayLabel } from '$lib/labels';
	import { cn } from '$lib/utils';
	import { CornerDownRight, ExternalLink } from '@lucide/svelte';
	import { getRunStatePresentation } from './presentation';
	import RunStateBadge from './RunStateBadge.svelte';
	import { runHref } from './run-links';
	import WrapAtSeparators from './WrapAtSeparators.svelte';
	type Entry = components['schemas']['DecisionEntryRead'];
	type RunState = components['schemas']['PipelineRunState'];
	/** Display labels for decision kinds; filter values stay the raw API kinds. */
	const KIND_LABELS: Record<string, string> = { 'run-question': 'Run question' };
	/**
	 * One observed decision. Attention marks only a row the operator can act on now
	 * (docs/steering/visual-style.md); a row that is not actionable says why.
	 */
	let {
		entry,
		projectName,
		busy = false,
		onreview
	}: {
		entry: Entry;
		projectName: string;
		busy?: boolean;
		onreview: () => void;
	} = $props();
	const linkClass = 'inline-flex min-h-6 items-center underline underline-offset-4';
	let answered = $derived(entry.question_state === 'answered');
	let status = $derived(answered ? 'Answer saved — resume pending' : 'Needs decision');
	let reason = $derived(
		`Nothing to decide while the run is ${getRunStatePresentation(entry.run_state as RunState).label.toLowerCase()}.`
	);
	let headingId = $derived(`decision-${entry.key}`);
</script>

<article
	aria-labelledby={headingId}
	data-attention={entry.actionable ? 'true' : undefined}
	class={cn(
		'flex flex-wrap items-center justify-between gap-4 rounded-lg border p-4',
		entry.actionable && 'border-l-3 border-l-attention-text'
	)}
>
	<div class="min-w-0 flex-1 space-y-1">
		<h2 id={headingId} class="text-base font-medium break-words">{entry.title}</h2>
		<p class="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
			<a class={linkClass} href={runHref(entry.run_id, entry.project_id)} data-run-link
				>Open PR run <span class="sr-only">for PR #{entry.pull_number}</span></a
			>
			<!-- `run_state` is an open string; unknown states fall back to a neutral label. -->
			<RunStateBadge state={entry.run_state as RunState} />
			<a class={cn(linkClass, 'gap-1')} href={entry.pull_url} target="_blank" rel="noreferrer"
				>PR #{entry.pull_number}<ExternalLink aria-hidden="true" class="size-3.5" /><span
					class="sr-only">(opens in a new tab)</span
				></a
			>
		</p>
		<p class="text-sm break-words">
			<a
				class={linkClass}
				href={`/projects/${encodeURIComponent(entry.project_id)}`}
				data-project-link>{projectName}</a
			>
			· {displayLabel(entry.kind, KIND_LABELS)} ·
			<span class="font-mono text-xs text-muted-foreground"
				><WrapAtSeparators text={entry.subject_id} /></span
			>
		</p>
		<div>
			<Badge variant={entry.actionable ? 'attention' : 'outline'}>
				{#if answered}<CornerDownRight aria-hidden="true" />{:else}<span
						aria-hidden="true"
						class={cn(
							'size-1.5 rounded-full',
							entry.actionable ? 'bg-attention-text' : 'bg-muted-foreground'
						)}
					></span>{/if}
				{status}
			</Badge>
		</div>
		<p class="text-xs text-muted-foreground">
			{entry.kind === 'run-question' ? 'Waiting since' : 'First observed waiting'}
			{new Date(entry.waiting_since).toLocaleString()} · Evidence observed {new Date(
				entry.observed_at
			).toLocaleString()}{#if entry.head_sha}
				· head <code>{entry.head_sha.slice(0, 8)}</code>{/if}
		</p>
	</div>
	<div class="flex flex-col items-end gap-1">
		<Button
			variant="outline"
			data-key={entry.key}
			disabled={busy || !entry.actionable}
			aria-label={`Review question: ${entry.title}`}
			aria-describedby={entry.actionable ? undefined : `${headingId}-reason`}
			onclick={onreview}>Review</Button
		>
		{#if !entry.actionable}<p
				id={`${headingId}-reason`}
				class="max-w-48 text-right text-xs text-muted-foreground"
			>
				{reason}
			</p>{/if}
	</div>
</article>
