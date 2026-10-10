<script lang="ts">
	import { Loader2, AlertCircle } from '@lucide/svelte';
	import type { CustomViewerConfig, InstalledViewer } from './types';
	import { repositoryDataSource, type RepositoryDataSource } from './data-source';
	import { loadViewer } from './viewer-loader';

	let {
		config,
		projectId,
		apiBase,
		ref,
		onfallback
	}: {
		config: CustomViewerConfig;
		projectId: string;
		apiBase: string;
		ref: string;
		onfallback: () => void;
	} = $props();
	let viewer = $state<InstalledViewer | null>(null);
	let error = $state('');
	let element = $state<HTMLElement & { dataSource?: RepositoryDataSource }>();
	const source = $derived(repositoryDataSource(projectId));

	$effect(() => {
		let active = true;
		viewer = null;
		error = '';
		void loadViewer(config)
			.then((installed) => {
				if (active) viewer = installed;
			})
			.catch((err: unknown) => {
				if (active) error = err instanceof Error ? err.message : 'Failed to load repository viewer';
			});
		return () => {
			active = false;
		};
	});

	$effect(() => {
		if (!element) return;
		element.dataSource = source;
		element.setAttribute('repo-id', projectId);
		element.setAttribute('api-base', apiBase);
		element.setAttribute('branch', ref);
		element.setAttribute('initial-path', viewer?.initialPath ?? '');
	});
</script>

<div class="h-[70vh] min-h-96 w-full">
	{#if error}
		<div
			role="alert"
			class="flex items-center gap-3 rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive"
		>
			<AlertCircle class="h-5 w-5 shrink-0" />
			<div>
				<p class="font-semibold">Could not load repository viewer</p>
				<p class="text-xs opacity-90">{error}</p>
				<button type="button" class="mt-2 underline" onclick={onfallback}>Use Git browser</button>
			</div>
		</div>
	{:else if !viewer}
		<div class="flex items-center justify-center gap-3 py-16 text-muted-foreground">
			<Loader2 class="h-6 w-6 animate-spin text-primary" />
			<p class="text-sm">Loading repository viewer…</p>
		</div>
	{:else}
		<svelte:element this={viewer.tagName} bind:this={element} class="block h-full w-full" />
	{/if}
</div>
