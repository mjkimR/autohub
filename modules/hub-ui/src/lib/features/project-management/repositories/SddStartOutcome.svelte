<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { runHref } from '../pipeline-runs/run-links';
	import WrapAtSeparators from '../pipeline-runs/WrapAtSeparators.svelte';
	import { intentLabel, intentUnit, type SddStarts } from './sdd-starts.svelte';
	import SddRequestDetails from './SddRequestDetails.svelte';
	import SddClaimRecovery from './SddClaimRecovery.svelte';
	import SddStartRefusal from './SddStartRefusal.svelte';
	/**
	 * Workspace-level recovery for the original request (CAP-SDD-native-delivery rule 13): it
	 * survives document and viewer-mode changes. With `results`, it also shows the settled outcome;
	 * the repository unit panel shows those beside its Start control instead.
	 */
	let {
		state,
		projectId,
		repository = '',
		results = false
	}: { state: SddStarts; projectId: string; repository?: string; results?: boolean } = $props();
	let visible = $derived(
		!!(state.pending || state.claimId || state.ownerConflict || state.resolved) ||
			(results && !!(state.runId || state.message || state.refusal))
	);
</script>

{#if visible}<div id="sdd-request-recovery" tabindex="-1" class="space-y-3">
		{#if state.claimId}
			{#key state.claimId}<SddClaimRecovery
					{projectId}
					{repository}
					claimId={state.claimId}
					intent={state.pending}
					busy={state.busy}
					onretry={() => state.retry()}
					onresolved={() => state.resolvedOwner()}
				/>{/key}
		{:else if state.pending}
			<section
				class="space-y-2 rounded-lg border bg-muted/40 p-3 text-sm"
				aria-label="Original activity request"
			>
				<h3 class="font-medium">
					{state.busy
						? 'Starting requested work…'
						: state.ownerConflict
							? 'Retained activity owner'
							: 'Start outcome unresolved'}
				</h3>
				<p class="break-words">
					{intentLabel(state.pending)} for
					<code><WrapAtSeparators text={intentUnit(state.pending)} /></code
					>{#if state.pending.kind === 'activity'}
						· base <code><WrapAtSeparators text={state.pending.body.base_branch} /></code>{/if}
				</p>
				{#if state.error}<p role="alert" class="text-destructive">{state.error}</p>{/if}
				<p class="text-xs text-muted-foreground">
					Competing starts remain unavailable. Recover this exact request; selecting another
					document does not replace it.
				</p>
				<Button size="sm" disabled={state.busy} onclick={() => state.retry()}>
					{state.busy ? 'Checking original request…' : 'Retry same request'}
				</Button>
				<SddRequestDetails intent={state.pending} {repository} />
			</section>
		{/if}
		{#if state.resolved}<p role="status" class="text-sm">{state.resolved}</p>{/if}
		{#if results}
			{#if state.runId}<Button variant="outline" href={runHref(state.runId, projectId)}
					>Open PR run</Button
				>{/if}
			{#if state.message}<p role="status" class="text-sm">{state.message}</p>{/if}
			{#if state.refusal}<SddStartRefusal refusal={state.refusal} {projectId} {repository} />{/if}
		{/if}
	</div>{/if}
