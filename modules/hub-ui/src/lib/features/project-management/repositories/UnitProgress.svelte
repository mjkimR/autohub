<script lang="ts">
	import { api, type components } from '$lib/api';
	import { responseData } from '$lib/api/pagination';
	import { Button } from '$lib/components/ui/button';
	import { readableLoadError } from '../pipeline-runs/load-errors';
	import ProgressList from './documents/ProgressList.svelte';
	import { runsByUnit } from './documents/progress';
	import type { RepositoryDocument } from './documents/model';
	/** The Progress section: repository units with the project's PR runs, read once per open. */
	const PAGE = 100,
		PAGES = 3;
	let {
		projectId,
		documents,
		onopen,
		openMilestonesOnly = false
	}: {
		projectId: string;
		documents: RepositoryDocument[];
		onopen: (path: string) => void;
		openMilestonesOnly?: boolean;
	} = $props();
	let runs = $state<Map<string, components['schemas']['PipelineRunRead'][]> | null>(null);
	let loading = $state(false);
	let error = $state('');
	let truncated = $state(false);
	let attempt = $state(0);
	$effect(() => {
		const project = projectId;
		void attempt;
		let active = true;
		loading = true;
		error = '';
		void (async () => {
			try {
				const items: components['schemas']['PipelineRunRead'][] = [];
				let total = 0;
				for (let page = 0; page < PAGES; page += 1) {
					const data = responseData(
						await api.GET('/api/v1/pipeline-runs', {
							params: { query: { project_id: project, limit: PAGE, offset: page * PAGE } }
						}),
						'Unable to load PR runs'
					);
					items.push(...data.items);
					total = data.total_count;
					if (items.length >= total || !data.items.length) break;
				}
				if (!active) return;
				runs = runsByUnit(items);
				truncated = items.length < total;
			} catch (e) {
				if (active)
					error = readableLoadError(e, "Couldn't load PR runs. Document statuses are still shown.");
			} finally {
				if (active) loading = false;
			}
		})();
		return () => {
			active = false;
		};
	});
</script>

<ProgressList {documents} {onopen} {runs} {projectId} {openMilestonesOnly}>
	{#snippet status()}
		{#if loading}<p role="status" class="text-xs text-muted-foreground">Loading PR runs…</p>
		{:else if error}<p role="alert" class="text-xs text-destructive">
				{error}
				<Button variant="link" size="sm" onclick={() => (attempt += 1)}>Retry PR runs</Button>
			</p>
		{:else if truncated}<p class="text-xs text-muted-foreground">
				PR runs come from the latest {PAGE * PAGES} runs in this project.
			</p>{/if}
	{/snippet}
</ProgressList>
