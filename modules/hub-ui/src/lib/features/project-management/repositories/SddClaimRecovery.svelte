<script lang="ts">
	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
	import { responseData } from '$lib/api/pagination';
	import { Button } from '$lib/components/ui/button';
	import { ExternalLink } from '@lucide/svelte';
	import { readableLoadError } from '../pipeline-runs/load-errors';
	import { runHref } from '../pipeline-runs/run-links';
	import WrapAtSeparators from '../pipeline-runs/WrapAtSeparators.svelte';
	import SddRequestDetails from './SddRequestDetails.svelte';
	import { intentLabel, intentUnit, type StartIntent } from './sdd-starts.svelte';
	import { activityLabel } from './sdd-unit';
	/**
	 * One card for a retained owner, titled by its situation with one next step. Evidence loads
	 * when the card opens; releasing an uncertain reservation still needs the explicit
	 * inspected-external-work acknowledgment (CAP-SDD-native-delivery rule 10).
	 */
	let {
		projectId,
		claimId,
		repository = '',
		intent = null,
		busy: requestBusy = false,
		onretry,
		onresolved
	}: {
		projectId: string;
		claimId: string;
		repository?: string;
		/** The retained original request, when this card belongs to one. */
		intent?: StartIntent | null;
		busy?: boolean;
		/** Replays the exact original request (useful once a live publication lease ends). */
		onretry?: () => void;
		onresolved: () => void;
	} = $props();
	let claim = $state<components['schemas']['ClaimRead'] | null>(null);
	let acknowledged = $state(false);
	let busy = $state(false);
	let error = $state('');
	let pending = $state<components['schemas']['ReconcileClaimRequest'] | null>(null);
	let now = $state(Date.now());
	let expires = $derived.by(() => {
		const value = claim?.checkpoint.lease_expires_at;
		return typeof value === 'string' ? Date.parse(value) : null;
	});
	let liveLease = $derived(expires !== null && (!Number.isFinite(expires) || expires > now));
	// Re-render when the lease ends, so the state never stays "live" past its expiry.
	$effect(() => {
		if (expires === null || !Number.isFinite(expires) || expires <= now) return;
		const timer = setTimeout(() => (now = Date.now()), Math.min(expires - now + 50, 2 ** 31 - 1));
		return () => clearTimeout(timer);
	});
	let releasable = $derived(
		!!claim && !claim.settled && !liveLease && !claim.run_id && claim.checkpoint.uncertain === true
	);
	let label = $derived(
		intent ? intentLabel(intent) : claim ? activityLabel(claim.activity) : 'This activity'
	);
	let unit = $derived(intent ? intentUnit(intent) : (claim?.unit ?? ''));
	let situation = $derived(
		!claim
			? 'has a retained owner'
			: claim.settled
				? 'has a settled owner'
				: claim.run_id
					? 'is owned by a PR run'
					: releasable
						? 'has an uncertain reservation'
						: 'is still being published'
	);
	let pullHref = $derived(
		/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repository) && claim?.checkpoint.pull_number
			? `https://github.com/${repository}/pull/${claim.checkpoint.pull_number}`
			: ''
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
				''
			);
			if (project === projectId && id === claimId) {
				claim = result;
				now = Date.now();
			}
		} catch (e) {
			error = readableLoadError(e, "Couldn't load the retained owner. Nothing was changed.");
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
				responseData(response, '');
				return;
			}
			if (project !== projectId || id !== claimId) return;
			claim = response.data;
			pending = null;
			onresolved();
		} catch (e) {
			error = readableLoadError(
				e,
				'The release was not confirmed. Retry the same acknowledgment to check it.'
			);
		} finally {
			busy = false;
		}
	}
	onMount(() => void inspect());
</script>

<section
	class="space-y-3 rounded-lg border bg-card p-3 text-sm"
	aria-label="Retained activity ownership"
>
	<h3 class="font-medium break-words">
		{unit ? `${label} for` : label}{#if unit}&nbsp;<code><WrapAtSeparators text={unit} /></code
			>{/if}{` ${situation}`}
	</h3>
	{#if !claim && busy}
		<p role="status" class="text-muted-foreground">Loading the retained owner…</p>
	{:else if claim?.settled}
		<p class="text-muted-foreground">
			This owner has settled. Review the activity intent before starting replacement work.
		</p>
		<Button size="sm" onclick={onresolved}>Review new activity</Button>
	{:else if claim?.run_id}
		<p class="text-muted-foreground">
			Its PR run owns this work. Follow that run; Hub refuses replacement work while it owns the
			unit.
		</p>
		<Button size="sm" href={runHref(claim.run_id, projectId)}>Open retained Run</Button>
	{:else if claim && releasable}
		<p class="text-muted-foreground">
			The publication outcome is uncertain and no Run has been confirmed. Inspect any external
			agent, branch and PR work before releasing this local reservation. Existing remote artifacts
			remain. This does not stop an agent or resume work.
		</p>
		<label class="flex min-h-6 items-center gap-2"
			><input type="checkbox" bind:checked={acknowledged} disabled={busy || !!pending} />I inspected
			the external work and acknowledge releasing this reservation.</label
		>
		<Button size="sm" disabled={busy || (!acknowledged && !pending)} onclick={reconcile}
			>{pending ? 'Retry same acknowledgment' : 'Release inspected reservation'}</Button
		>
	{:else if claim}
		<p class="text-muted-foreground">
			This activity or its publication lease still owns the work. Inspect again after the current
			publication settles, then retry the same request. A live owner cannot be released here.
		</p>
	{/if}
	{#if error}<p role="alert" class="text-destructive">{error}</p>{/if}
	{#if claim || error}
		<div class="flex flex-wrap gap-2">
			<Button size="sm" variant="ghost" disabled={busy || !!pending} onclick={inspect}
				>Inspect again</Button
			>
			{#if pullHref}<Button
					size="sm"
					variant="ghost"
					href={pullHref}
					target="_blank"
					rel="noreferrer"
					><ExternalLink aria-hidden="true" />Original PR #{claim?.checkpoint.pull_number}<span
						class="sr-only">(opens in a new tab)</span
					></Button
				>{/if}
			{#if claim && !claim.settled && !claim.run_id && !releasable && intent && onretry}<Button
					size="sm"
					variant="outline"
					disabled={requestBusy}
					onclick={onretry}>Retry same request</Button
				>{/if}
		</div>
	{/if}
	<SddRequestDetails {intent} {repository} {claimId} />
</section>
