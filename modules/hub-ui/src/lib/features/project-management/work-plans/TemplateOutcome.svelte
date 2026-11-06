<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import type { TemplateIntent } from './template-intent.svelte';
	let { intent, refresh }: { intent: TemplateIntent; refresh: () => Promise<void> } = $props();
	let refreshError = $state('');
	async function reload() {
		try {
			await refresh();
			refreshError = '';
		} catch (e) {
			refreshError = e instanceof Error ? e.message : 'Refresh failed';
		}
	}
</script>

{#if intent.pending}
	<section class="space-y-2 rounded-lg border p-4" aria-label="Original template request">
		<p>
			{intent.pending.op} · Request {intent.pending.body.request_id} · {intent.state === 'unknown'
				? 'Outcome unknown'
				: intent.state}
		</p>
		{#if intent.outcome}
			{#if intent.outcome.refresh_error}<p role="alert">{intent.outcome.refresh_error}</p>{/if}
			<p>
				Original template: {intent.outcome.original_template?.name} · {intent.outcome
					.original_template?.id} · revision {intent.outcome.original_template?.revision}
			</p>
			<p>
				Current template revision: {intent.outcome.current_template?.revision} · {intent.outcome
					.current_template?.deleted
					? 'Deleted'
					: 'Retained'}
			</p>
			{#if intent.outcome.original_plan}<p>
					Original Plan: {intent.outcome.original_plan.id} · {intent.outcome.original_plan.state}
				</p>
				<p>Current Plan: {intent.outcome.current_plan?.state}</p>
				<a
					class="underline"
					href={`/projects/${intent.project}?tab=plans&plan_id=${intent.outcome.original_plan.id}`}
					>Open original Plan</a
				>{/if}
			{#if intent.outcome.source_plan_id}<p>
					Source Plan: {intent.outcome.source_plan_id} · revision {intent.outcome.source_revision}
				</p>{/if}
			{#if intent.outcome.omitted?.length}<p>Omitted: {intent.outcome.omitted?.join(', ')}</p>{/if}
		{/if}
		{#if intent.error}<p role="alert">{intent.error}</p>{/if}
		<Button type="button" variant="outline" disabled={intent.busy} onclick={() => intent.check()}
			>Check original request</Button
		>
		{#if intent.state === 'unknown'}<Button
				type="button"
				variant="outline"
				disabled={intent.busy}
				onclick={() => intent.retry()}>Retry same request</Button
			>{/if}
		{#if intent.state === 'recorded'}<Button type="button" variant="outline" onclick={reload}
				>Refresh current state</Button
			>{/if}
		{#if !intent.locked}<Button type="button" variant="ghost" onclick={() => intent.dismiss()}
				>Dismiss recorded/refused request</Button
			>{/if}
		{#if refreshError}<p role="alert">
				Recorded result retained. Refresh failed: {refreshError}
			</p>{/if}
	</section>
{/if}
