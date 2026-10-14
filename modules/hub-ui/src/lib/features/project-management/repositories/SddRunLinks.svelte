<script lang="ts">
	import { api, type components } from '$lib/api';
	import { responseData } from '$lib/api/pagination';
	import { Badge } from '$lib/components/ui/badge';
	import { getStateBadgeClass } from '../pipeline-runs/presentation';
	let {
		projectId,
		specDir,
		refresh = ''
	}: { projectId: string; specDir: string; refresh?: string } = $props();
	let runs = $state<components['schemas']['PipelineRunRead'][]>([]);
	let error = $state('');
	let loading = $state(false);
	let retry = $state(0);
	$effect(() => {
		const project = projectId,
			spec = specDir;
		void refresh;
		void retry;
		runs = [];
		error = '';
		const valid = /^specs\/\d{4}-\d{2}\/[a-zA-Z0-9_-]+$/.test(spec);
		loading = valid;
		if (!valid) return;
		let active = true;
		const timer = setTimeout(async () => {
			try {
				const result = responseData(
					await api.GET('/api/v1/projects/{project_id}/sdd/runs', {
						params: { path: { project_id: project }, query: { spec_dir: spec } }
					}),
					'Unable to load related executions'
				);
				if (active) runs = result;
			} catch (e) {
				if (active) error = e instanceof Error ? e.message : 'Unable to load related executions';
			} finally {
				if (active) loading = false;
			}
		}, 250);
		return () => {
			active = false;
			clearTimeout(timer);
		};
	});
</script>

{#if specDir}
	<div class="space-y-2 border-t pt-3">
		<h4 class="text-xs font-semibold text-muted-foreground">Recent executions for this spec</h4>
		{#if loading}<p class="text-xs text-muted-foreground">Loading executions…</p>
		{:else if error}<p role="status" class="text-xs text-destructive">
				{error}
				<button
					type="button"
					class="underline"
					onclick={() => {
						retry += 1;
					}}>Retry</button
				>
			</p>
		{:else if !runs.length}<p class="text-xs text-muted-foreground">
				No executions found. Check readiness to start from an existing PR.
			</p>
		{:else}
			<ul class="space-y-2">
				{#each runs as run (run.id)}<li>
						<a
							class="flex flex-wrap items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-muted"
							href={`/projects/runs?run=${run.id}&view=decisions`}
						>
							<span class="font-medium">PR #{run.pull_number}</span>
							<Badge variant="outline" class={getStateBadgeClass(run.state)}
								>{run.state.replaceAll('_', ' ')}</Badge
							>
							<span class="min-w-0 break-words">{run.pull_snapshot.title}</span>
						</a>
					</li>{/each}
			</ul>
			<p class="text-xs text-muted-foreground">Latest {runs.length} executions · up to 20 shown</p>
		{/if}
	</div>
{/if}
