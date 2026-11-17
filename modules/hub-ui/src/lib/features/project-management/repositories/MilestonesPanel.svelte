<script lang="ts">
	import { goto } from '$app/navigation';
	import type { components } from '$lib/api';
	import { Button } from '$lib/components/ui/button';
	import { readableLoadError } from '../pipeline-runs/load-errors';
	import { repositoryDataSource, type RepositoryDataSource } from './data-source';
	import { discoverDocuments } from './documents/discovery';
	import type { RepositoryDocument } from './documents/model';
	import { cacheRepositoryReads } from './documents/read-cache';
	import UnitProgress from './UnitProgress.svelte';
	/**
	 * The project's open milestones on the default branch with their direct proposal members and
	 * latest PR runs. Read-only: units open in the Repository tab (CAP-DOC-repository-viewer 10).
	 */
	let {
		project,
		dataSource
	}: {
		project: components['schemas']['ProjectRead'];
		dataSource?: RepositoryDataSource;
	} = $props();
	const reads = $derived(dataSource ?? repositoryDataSource(project.id));
	let branch = $state('');
	let documents = $state<RepositoryDocument[]>([]);
	let errors = $state<string[]>([]);
	let error = $state('');
	let loading = $state(true);
	let attempt = $state(0);
	$effect(() => {
		const source = cacheRepositoryReads(reads);
		void attempt;
		const controller = new AbortController();
		loading = true;
		error = '';
		errors = [];
		void (async () => {
			try {
				const ref = (await source.info(controller.signal)).default_branch;
				branch = ref;
				const listing = await discoverDocuments(source, ref, 'milestones', controller.signal);
				if (controller.signal.aborted) return;
				documents = listing.documents;
				errors = listing.errors;
			} catch (e) {
				if (!controller.signal.aborted)
					error = readableLoadError(e, "Couldn't load milestones from the repository.");
			} finally {
				if (!controller.signal.aborted) loading = false;
			}
		})();
		return () => controller.abort();
	});
	const open = (path: string) => {
		const query = new URLSearchParams({ tab: 'repository', path, ref: branch });
		void goto(`/projects/${encodeURIComponent(project.id)}?${query}`);
	};
</script>

<section aria-labelledby="milestones-heading" class="max-w-3xl space-y-4">
	<div class="space-y-1">
		<h2 id="milestones-heading" class="text-lg font-semibold">Open milestones</h2>
		<p class="text-sm text-muted-foreground">
			Planned and active milestones on {branch
				? `the default branch (${branch})`
				: 'the default branch'}
			with their proposals. Done and dropped milestones stay in the Repository tab's Progress.
		</p>
	</div>
	{#if loading}<p role="status" class="text-sm text-muted-foreground">Loading milestones…</p>
	{:else if error || errors.length}
		<div role="alert" class="space-y-2 rounded-lg border p-3 text-sm">
			<p class="font-medium">Milestone listing incomplete</p>
			{#if error}<p>{error}</p>{/if}
			{#each errors as item (item)}<p class="break-words">{item}</p>{/each}
			<Button variant="outline" size="sm" onclick={() => (attempt += 1)}>Retry milestones</Button>
		</div>
	{/if}
	{#if !loading && !error}
		<UnitProgress projectId={project.id} {documents} onopen={open} openMilestonesOnly />
	{/if}
</section>
