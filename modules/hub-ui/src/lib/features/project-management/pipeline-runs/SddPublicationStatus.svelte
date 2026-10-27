<script lang="ts">
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { Button } from '$lib/components/ui/button';
	let {
		row,
		runId,
		disabled = false,
		onchange
	}: {
		row: Record<string, unknown>;
		runId: string;
		disabled?: boolean;
		onchange: () => void | Promise<void>;
	} = $props();
	let publication = $derived((row.publication || {}) as Record<string, unknown>);
	let request = $derived(row.request as components['schemas']['ResumeRunRequest'] | undefined);
	let pending = $derived(
		['preparing', 'prepared', 'uncertain'].includes(String(publication.state))
	);
	let busy = $state(false);
	let error = $state('');
	async function retry() {
		if (!request || busy || disabled) return;
		busy = true;
		error = '';
		try {
			const result = await api.POST('/api/v1/pipeline-runs/{run_id}/resume', {
				params: { path: { run_id: runId } },
				body: request
			});
			if (result.error)
				throw new Error(apiErrorMessage(result.error, 'Could not reconcile decision'));
			await onchange();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not reconcile decision';
		} finally {
			busy = false;
		}
	}
</script>

{#if publication.state}
	<div class="space-y-2 rounded-md border p-2 text-xs">
		<p class="font-medium">Publication: {String(publication.state)}</p>
		{#if pending}
			<p>
				The result is not confirmed. Reconcile the saved request to check the remote commit and
				safely retry the same decision. A canceled run is never approved by recovery.
			</p>
			{#if request && !String(row.actor).startsWith('policy:')}<Button
					size="sm"
					variant="outline"
					disabled={busy || disabled}
					onclick={retry}>{busy ? 'Reconciling…' : 'Reconcile decision'}</Button
				>{/if}
			{#if String(row.actor).startsWith('policy:')}<p>
					Resume inspection to reconcile this automatic policy decision.
				</p>{/if}
		{:else if publication.applied === false}<p>
				Published to Git; approval was not applied because this run or project changed.
			</p>{/if}
		{#if error}<p role="alert" class="text-destructive">{error}</p>{/if}
	</div>
{/if}
