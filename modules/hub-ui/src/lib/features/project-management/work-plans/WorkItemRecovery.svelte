<script lang="ts">
	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { Button } from '$lib/components/ui/button';
	import { Textarea } from '$lib/components/ui/textarea';
	type Item = components['schemas']['WorkItemRead'];
	type Recovery = components['schemas']['WorkItemRecoveryRead'];
	type Command = components['schemas']['WorkItemRecover'];
	let {
		projectId,
		planId,
		revision,
		baseBranch,
		item,
		refresh
	}: {
		projectId: string;
		planId: string;
		revision: number;
		baseBranch: string;
		item: Item;
		refresh: () => Promise<void>;
	} = $props();
	let confirming = $state(false);
	let reason = $state('');
	let busy = $state(false);
	let error = $state('');
	let status = $state('');
	let history = $state<Recovery[]>([]);
	let total = $state(0);
	let loaded = $state(false);
	let uncertain = $state(false);
	const storageKey = $derived(`work-item-recovery:${projectId}:${item.id}`);
	const path = $derived({ project_id: projectId, plan_id: planId, item_id: item.id });

	async function loadHistory(more = false) {
		busy = true;
		try {
			const result = await api.GET(
				'/api/v1/projects/{project_id}/work-plans/{plan_id}/items/{item_id}/recoveries',
				{
					params: { path, query: { offset: more ? history.length : 0, limit: 10 } }
				}
			);
			if (!result.data)
				throw new Error(apiErrorMessage(result.error, 'Could not load recovery history'));
			history = more ? [...history, ...result.data.items] : result.data.items;
			total = result.data.total_count;
			loaded = true;
			const saved = sessionStorage.getItem(storageKey);
			if (saved) {
				const requestId = (JSON.parse(saved) as Command).request_id;
				const known = history.find((record) => record.request_id === requestId);
				if (known) {
					sessionStorage.removeItem(storageKey);
					uncertain = false;
					status = `Recovery ${known.state}: ${known.detail}`;
				}
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not load recovery history';
		} finally {
			busy = false;
		}
	}
	async function submit() {
		busy = true;
		error = '';
		status = 'Checking recovery';
		try {
			const saved = sessionStorage.getItem(storageKey);
			const command: Command = saved
				? JSON.parse(saved)
				: {
						request_id: crypto.randomUUID(),
						expected_revision: revision,
						expected_run_revision: item.recovery?.run_revision ?? null,
						reason: reason.trim()
					};
			sessionStorage.setItem(storageKey, JSON.stringify(command));
			const result = await api.POST(
				'/api/v1/projects/{project_id}/work-plans/{plan_id}/items/{item_id}/recover',
				{
					params: { path },
					body: command
				}
			);
			if (!result.data) {
				if (result.response.status >= 400 && result.response.status < 500) {
					sessionStorage.removeItem(storageKey);
					uncertain = false;
					status = 'Refused; refresh evidence and confirm again';
				} else uncertain = true;
				throw new Error(apiErrorMessage(result.error, 'Recovery could not be confirmed'));
			}
			sessionStorage.removeItem(storageKey);
			uncertain = false;
			status = `Recovery ${result.data.recovery.state}: ${result.data.recovery.detail}`;
			confirming = false;
			await refresh();
			await loadHistory();
		} catch (e) {
			uncertain = !!sessionStorage.getItem(storageKey);
			error = e instanceof Error ? e.message : 'Response lost; check the original recovery request';
		} finally {
			busy = false;
		}
	}
	onMount(() => {
		uncertain = !!sessionStorage.getItem(storageKey);
	});
	function open() {
		confirming = true;
		uncertain = !!sessionStorage.getItem(storageKey);
	}
</script>

<section class="space-y-2 border-t pt-3" aria-label={`Recovery for ${item.key}`}>
	{#if item.recovery?.pending_state}
		<p role="status">
			Recovery {item.recovery.pending_state}. {item.recovery.pending_detail ??
				'Refresh recovery status for the current hold or progress.'}
		</p>
	{:else if item.recovery?.eligible}
		<Button variant="outline" size="sm" onclick={open}>Retry Work Item</Button>
	{:else if item.recovery}
		<p class="text-muted-foreground">
			Retry unavailable: {item.recovery.reason}. {item.recovery.next_action}
		</p>
	{/if}
	{#if confirming}
		<div class="space-y-2 rounded border p-3">
			<p>
				Retry unchanged work into {baseBranch}. Previous result: {item.state}: {item.detail ??
					'Inspect execution history'}.
			</p>
			<p>
				Successful Work Items stay complete. The original Run and its budget counters are retained.
			</p>
			{#if item.pull_url}<a class="underline" href={item.pull_url}>Inspect original PR</a>{/if}
			<label class="block"
				>Recovery reason
				<Textarea bind:value={reason} maxlength={500} disabled={busy || uncertain} />
			</label>
			<Button size="sm" onclick={submit} disabled={busy || (!uncertain && !reason.trim())}
				>{uncertain ? 'Check original request' : 'Confirm retry'}</Button
			>
			<Button variant="ghost" size="sm" onclick={() => (confirming = false)} disabled={busy}
				>Cancel</Button
			>
		</div>
	{/if}
	{#if status}<p role="status">{status}</p>{/if}
	{#if error}<p role="alert">{error}</p>{/if}
	{#if uncertain}<Button size="sm" onclick={submit} disabled={busy}>Check original request</Button
		>{/if}
	<div class="flex gap-2">
		<Button variant="ghost" size="sm" onclick={() => loadHistory()} disabled={busy}
			>Inspect recovery history</Button
		>
		<Button
			variant="ghost"
			size="sm"
			onclick={async () => {
				await refresh();
				await loadHistory();
			}}
			disabled={busy}>Refresh recovery status</Button
		>
	</div>
	{#if busy}<p role="status">Checking recovery</p>{/if}
	{#if loaded && !history.length}<p>
			No recovery history. The current result is the legacy execution outcome.
		</p>{/if}
	{#each history as record (record.id)}
		<details class="rounded border p-2">
			<summary
				>{record.state} · {record.reason} · {new Date(record.created_at).toLocaleString()}</summary
			>
			<p>{record.actor} · Previous result: {String(record.prior_outcome.state)}</p>
			<p>{record.detail}</p>
			{#if record.prior_outcome.pipeline_run_id}<a
					class="underline"
					href={`/projects/runs?run=${record.prior_outcome.pipeline_run_id}`}>Original execution</a
				>{/if}
			{#each record.events as event (event.id)}<p>{event.kind}: {event.detail}</p>{/each}
		</details>
	{/each}
	{#if history.length < total}<Button
			variant="ghost"
			size="sm"
			onclick={() => loadHistory(true)}
			disabled={busy}>Load more recoveries</Button
		>{/if}
</section>
