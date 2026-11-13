<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { runHref } from '../pipeline-runs/run-links';
	import type { SddStarts } from './sdd-starts.svelte';
	import SddClaimRecovery from './SddClaimRecovery.svelte';
	let {
		state,
		projectId,
		repository = ''
	}: { state: SddStarts; projectId: string; repository?: string } = $props();
</script>

{#if state.pending}
	<div
		class="space-y-2 rounded-lg border bg-muted/40 p-3"
		role="region"
		aria-label="Original activity request"
	>
		<p class="text-sm font-medium">
			{state.busy
				? 'Starting requested work…'
				: state.ownerConflict
					? 'Retained activity owner'
					: 'Start outcome unresolved'}
		</p>
		<p class="text-xs break-all">
			Repository {repository || state.pending.project} · project {state.pending.project} · {#if state.pending.kind === 'activity'}
				PROP-{state.pending.slug} · {state.pending.activity === 'plan' ? 'Planning' : 'Development'} ·
				base {state.pending.body.base_branch} · request {state.pending.body.request_id}
			{:else}
				{state.pending.body.spec_dir} · PR #{state.pending.body.pull_number}
			{/if}
			· effort {state.pending.body.activity_effort || 'repository recommendation'} · catalog {state
				.pending.body.catalog || 'project default'}
		</p>
		<p class="text-xs text-muted-foreground">
			Competing starts remain unavailable. Inspect the original owner or recover this exact request;
			selecting another document does not replace it.
		</p>
		<Button size="sm" variant="outline" disabled={state.busy} onclick={() => state.retry()}>
			{state.busy ? 'Checking original request…' : 'Retry same request'}
		</Button>
	</div>
{/if}
{#if state.claimId}
	{#key state.claimId}<SddClaimRecovery
			{projectId}
			{repository}
			claimId={state.claimId}
			onresolved={() => state.resolvedOwner()}
		/>{/key}
{:else if state.ownerConflict}
	<p class="text-xs text-muted-foreground">
		Inspect the retained Run or PR links. Existing or uncertain external work must be settled before
		replacement work can start; retry alone does not release ownership.
	</p>
{/if}
{#if state.runId}<Button variant="outline" href={runHref(state.runId, projectId)}
		>Open PR run</Button
	>{/if}
{#if state.message}<p role="status" class="text-sm">{state.message}</p>{/if}
{#if state.error}<p role="alert" class="text-sm text-destructive">{state.error}</p>{/if}
