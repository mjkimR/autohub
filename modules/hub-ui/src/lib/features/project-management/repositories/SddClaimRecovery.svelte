<script lang="ts">
	import { api, type components } from '$lib/api';
	import { responseData } from '$lib/api/pagination';
	import { Button } from '$lib/components/ui/button';
	import { runHref } from '../pipeline-runs/run-links';
	let {
		projectId,
		claimId,
		repository = '',
		onresolved
	}: { projectId: string; claimId: string; repository?: string; onresolved: () => void } = $props();
	let claim = $state<components['schemas']['ClaimRead'] | null>(null);
	let acknowledged = $state(false);
	let busy = $state(false);
	let error = $state('');
	let pending = $state<components['schemas']['ReconcileClaimRequest'] | null>(null);
	let liveLease = $derived.by(() => {
		const expires = claim?.checkpoint.lease_expires_at;
		if (typeof expires !== 'string') return false;
		const parsed = Date.parse(expires);
		return !Number.isFinite(parsed) || parsed > Date.now();
	});
	let releasable = $derived(
		!!claim &&
			!claim.settled &&
			!liveLease &&
			(claim.retired ||
				(!claim.run_id &&
					claim.checkpoint.execution_version === 2 &&
					claim.checkpoint.uncertain === true))
	);

	async function inspect() {
		const project = projectId,
			id = claimId;
		busy = true;
		error = '';
		acknowledged = false;
		try {
			const result = responseData(
				await api.GET('/api/v1/projects/{project_id}/sdd/claims/{claim_id}', {
					params: { path: { project_id: project, claim_id: id } }
				}),
				'Unable to inspect the retained owner'
			);
			if (project === projectId && id === claimId) claim = result;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unable to inspect the retained owner';
		} finally {
			busy = false;
		}
	}
	async function reconcile() {
		const project = projectId,
			id = claimId;
		if (!claim || (!pending && (!acknowledged || !releasable)) || busy) return;
		pending ||= {
			request_id: crypto.randomUUID(),
			expected_checkpoint_digest: claim.checkpoint_digest,
			acknowledge_external_work: true
		};
		busy = true;
		error = '';
		try {
			const response = await api.POST(
				'/api/v1/projects/{project_id}/sdd/claims/{claim_id}/reconcile',
				{
					params: { path: { project_id: project, claim_id: id } },
					body: pending
				}
			);
			if (!response.data) {
				if (response.response.status >= 400 && response.response.status < 500) {
					pending = null;
					acknowledged = false;
				}
				responseData(response, 'Reconciliation was not confirmed; retry the same acknowledgment');
				return;
			}
			if (project !== projectId || id !== claimId) return;
			claim = response.data;
			pending = null;
			onresolved();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Reconciliation was not confirmed';
		} finally {
			busy = false;
		}
	}
</script>

<section class="space-y-2 rounded-lg border p-3" aria-label="Retained activity ownership">
	<p class="text-sm font-medium">Retained activity owner</p>
	<Button size="sm" variant="outline" disabled={busy || !!pending} onclick={inspect}
		>Inspect retained owner</Button
	>
	{#if claim}
		<p class="text-xs break-all">{claim.unit} · {claim.activity} · claim {claim.id}</p>
		{#if claim.run_id}<Button size="sm" variant="link" href={runHref(claim.run_id, projectId)}
				>Open retained Run</Button
			>{/if}
		{#if repository && claim.checkpoint.pull_number}<Button
				size="sm"
				variant="link"
				href={`https://github.com/${repository}/pull/${claim.checkpoint.pull_number}`}
				target="_blank"
				rel="noreferrer">Inspect original PR</Button
			>{/if}
		{#if releasable}
			<p class="text-xs text-muted-foreground">
				{claim.retired
					? "Hub's native workflow execution is retired."
					: 'The publication outcome is uncertain and no Run has been confirmed.'} Inspect any external
				agent, branch and PR work before releasing this local reservation. Existing remote artifacts remain.
				This does not stop an agent or resume work.
			</p>
			<label class="flex items-center gap-2 text-sm"
				><input type="checkbox" bind:checked={acknowledged} disabled={busy || !!pending} />I
				inspected the external work and acknowledge releasing this reservation.</label
			>
			<Button
				size="sm"
				variant="outline"
				disabled={busy || (!acknowledged && !pending)}
				onclick={reconcile}
				>{pending ? 'Retry same acknowledgment' : 'Release inspected reservation'}</Button
			>
		{:else if claim.settled}
			<p class="text-xs text-muted-foreground">
				This owner has settled. Review the activity intent before starting replacement work.
			</p>
			<Button size="sm" variant="outline" onclick={onresolved}>Review new activity</Button>
		{:else}
			<p class="text-xs text-muted-foreground">
				This activity or its publication lease still owns the work. Follow its Run, or inspect again
				after the current publication settles. A live owner cannot be released here.
			</p>
		{/if}
	{/if}
	{#if error}<p role="alert" class="text-sm text-destructive">{error}</p>{/if}
</section>
