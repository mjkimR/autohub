<script lang="ts">
	import { api } from '$lib/api';
	import { Button } from '$lib/components/ui/button';
	import { History, RefreshCw } from '@lucide/svelte';
	import { responseData } from '$lib/api/pagination';
	let { runId, revision }: { runId: string; revision: number } = $props();
	let rows = $state<Record<string, unknown>[]>([]);
	let error = $state('');
	let loading = $state(true);
	let refresh = $state(0);
	let expanded = $state(false);
	let visibleRows = $derived(expanded ? rows : rows.slice(0, 5));
	const labels: Record<string, string> = {
		approve: 'Integration approved',
		revise: 'Changes requested',
		revoke: 'Approval withdrawn',
		reject: 'Run stopped',
		resume: 'Run resumed'
	};
	function date(value: unknown) {
		const parsed = new Date(String(value || ''));
		return Number.isNaN(parsed.getTime()) ? 'Time unavailable' : parsed.toLocaleString();
	}
	$effect(() => {
		const id = runId;
		void revision;
		void refresh;
		loading = true;
		let active = true;
		rows = [];
		error = '';
		void (async () => {
			try {
				const response = await api.GET('/api/v1/pipeline-runs/{run_id}/specrig-decisions', {
					params: { path: { run_id: id } }
				});
				const data: unknown = responseData(response, 'Unable to load decision history');
				if (!Array.isArray(data)) throw new Error('Invalid decision history');
				if (active)
					rows = data.filter(
						(row): row is Record<string, unknown> => !!row && typeof row === 'object'
					);
			} catch (e) {
				if (active) error = e instanceof Error ? e.message : 'Unable to load decision history';
			} finally {
				if (active) loading = false;
			}
		})();
		return () => {
			active = false;
		};
	});
</script>

<section class="space-y-4" aria-label="Approval activity">
	<div class="flex items-center justify-between gap-2">
		<h3 class="flex items-center gap-2 text-sm font-semibold">
			<History class="size-4 text-muted-foreground" />Approval activity
		</h3>
		<Button
			variant="ghost"
			size="icon"
			class="size-7"
			aria-label="Refresh approval history"
			disabled={loading}
			onclick={() => {
				refresh += 1;
			}}><RefreshCw class={loading ? 'size-3.5 animate-spin' : 'size-3.5'} /></Button
		>
	</div>
	{#if loading}<p role="status" class="animate-pulse text-xs text-muted-foreground">
			Loading decision history…
		</p>
	{:else if error}<p role="status" class="text-xs text-destructive">
			{error}. Use refresh to retry.
		</p>
	{:else if !rows.length}<p class="text-xs leading-relaxed text-muted-foreground">
			No integration decisions yet. Approvals and change requests will appear here.
		</p>
	{:else}
		<ol class="space-y-4 border-l pl-4">
			{#each visibleRows as row (row.id)}
				<li
					class="relative space-y-1.5 before:absolute before:top-1.5 before:-left-[21px] before:size-2 before:rounded-full before:border-2 before:border-background before:bg-muted-foreground"
				>
					<p class="text-xs font-semibold">
						{labels[String(row.action)] || String(row.action || 'Decision')}
					</p>
					<p class="text-xs break-words text-muted-foreground">
						{row.actor === 'github:pr-ready'
							? 'GitHub · PR ready'
							: String(row.actor || 'Actor unavailable')}
					</p>
					<time class="block text-xs text-muted-foreground">{date(row.created_at)}</time>
					{#if row.feedback}<p
							class="rounded-md bg-muted/50 p-2 text-xs leading-relaxed break-words whitespace-pre-wrap"
						>
							{String(row.feedback)}
						</p>{/if}
					<details class="text-xs text-muted-foreground">
						<summary class="cursor-pointer">Inspected revision</summary>
						<div class="mt-2 space-y-1 break-all">
							<p>Head <code>{String(row.head_sha || 'Unavailable')}</code></p>
							<p>Base <code>{String(row.base_sha || 'Unavailable')}</code></p>
						</div>
					</details>
				</li>
			{/each}
		</ol>
		{#if rows.length > 5}<Button
				variant="ghost"
				size="sm"
				onclick={() => {
					expanded = !expanded;
				}}>{expanded ? 'Show fewer decisions' : `Show all ${rows.length} decisions`}</Button
			>{/if}
		<p class="text-xs text-muted-foreground">Latest {rows.length} decisions · up to 100 shown</p>
	{/if}
</section>
