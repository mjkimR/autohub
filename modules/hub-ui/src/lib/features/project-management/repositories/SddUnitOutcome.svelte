<script lang="ts">
	import WrapAtSeparators from '../pipeline-runs/WrapAtSeparators.svelte';
	import { tick, untrack } from 'svelte';
	import { Button } from '$lib/components/ui/button';
	import { CircleCheck } from '@lucide/svelte';
	import { runHref } from '../pipeline-runs/run-links';
	import { intentLabel, intentUnit, sddStarts } from './sdd-starts.svelte';
	import SddStartRefusal from './SddStartRefusal.svelte';
	/**
	 * The start outcome beside the Start control that caused it. Exact recovery of an unresolved
	 * request stays in the workspace region (CAP-SDD-native-delivery rule 13); this panel names
	 * why new starts are unavailable and links to it.
	 */
	let {
		projectId,
		unit,
		repository = ''
	}: { projectId: string; unit: string; repository?: string } = $props();
	const starts = $derived(sddStarts(projectId));
	let here = $derived(starts.lastUnit === unit);
	let shown = $derived(
		(!!starts.pending && !starts.busy) || (here && !!(starts.refusal || starts.runId))
	);
	let element = $state<HTMLDivElement>();
	// Focus only outcomes that settle while this panel is open, never a remembered older one.
	let seen = untrack(() => starts.outcomeVersion);
	$effect(() => {
		const version = starts.outcomeVersion;
		if (version === seen) return;
		seen = version;
		if (untrack(() => here)) void tick().then(() => element?.focus());
	});
	function reviewRecovery() {
		const target = document.getElementById('sdd-request-recovery');
		target?.scrollIntoView?.({ block: 'start' });
		target?.focus({ preventScroll: true });
	}
</script>

{#if shown}<div bind:this={element} tabindex="-1">
		{#if starts.pending && !starts.busy}
			<div role="status" class="space-y-2 rounded-lg border bg-muted/40 p-3 text-sm">
				<p>
					New starts are unavailable while the original {intentLabel(starts.pending)} request for
					<code class="break-words"><WrapAtSeparators text={intentUnit(starts.pending)} /></code> is unresolved.
				</p>
				<Button size="sm" variant="outline" onclick={reviewRecovery}
					>Review the original request</Button
				>
			</div>
		{:else if here && starts.refusal}
			<SddStartRefusal refusal={starts.refusal} {projectId} {repository} />
		{:else if here && starts.runId}
			<div role="status" class="space-y-3 rounded-lg border p-3 text-sm">
				<p class="flex items-start gap-2">
					<CircleCheck class="mt-0.5 size-4 shrink-0" aria-hidden="true" />{starts.message}
				</p>
				<Button size="sm" href={runHref(starts.runId, projectId)}>Open PR run</Button>
			</div>
		{/if}
	</div>{/if}
