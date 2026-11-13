<script lang="ts">
	import { api } from '$lib/api';
	import { Button } from '$lib/components/ui/button';
	import { responseData } from '$lib/api/pagination';
	let { runId, revision }: { runId: string; revision: number } = $props();
	let rows = $state<Record<string, unknown>[]>([]);
	let error = $state('');
	let loading = $state(true);
	let refresh = $state(0);
	$effect(() => {
		const id = runId;
		void revision;
		void refresh;
		let active = true;
		loading = true;
		error = '';
		rows = [];
		void (async () => {
			try {
				const data: unknown = responseData(
					await api.GET('/api/v1/pipeline-runs/{run_id}/sdd-decisions', {
						params: { path: { run_id: id } }
					}),
					'Unable to load retained decision history'
				);
				if (!Array.isArray(data)) throw new Error('Invalid decision history');
				if (active)
					rows = data.filter(
						(row): row is Record<string, unknown> => !!row && typeof row === 'object'
					);
			} catch (e) {
				if (active)
					error = e instanceof Error ? e.message : 'Unable to load retained decision history';
			} finally {
				if (active) loading = false;
			}
		})();
		return () => {
			active = false;
		};
	});
</script>

<section class="space-y-3" aria-label="Retained native decisions">
	<h3 class="text-sm font-semibold">Retained native decisions</h3>
	<p class="text-xs text-muted-foreground">
		Historical records only. These decisions grant no new execution or merge authority.
	</p>
	<Button size="sm" variant="ghost" disabled={loading} onclick={() => (refresh += 1)}
		>Refresh retained decisions</Button
	>
	{#if loading}<p role="status" class="text-xs text-muted-foreground">
			Loading retained decision history…
		</p>
	{:else if error}<p role="alert" class="text-xs text-destructive">{error}</p>
	{:else if !rows.length}<p class="text-xs text-muted-foreground">No retained native decisions.</p>
	{:else}<ol class="space-y-2">
			{#each rows as row, index (String(row.id || index))}<li class="rounded-lg border p-3 text-xs">
					<p class="font-medium">
						{String(row.action || 'Decision')} · {String(row.actor || 'Actor unavailable')}
					</p>
					<p class="text-muted-foreground">{String(row.created_at || 'Time unavailable')}</p>
					<details class="mt-2">
						<summary class="cursor-pointer">Recorded decision</summary>
						<pre class="mt-2 overflow-auto break-all whitespace-pre-wrap">{JSON.stringify(
								row,
								null,
								2
							)}</pre>
					</details>
				</li>{/each}
		</ol>{/if}
</section>
