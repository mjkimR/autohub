<script lang="ts">
	import { onMount } from 'svelte';
	import { Loader2, AlertCircle } from '@lucide/svelte';
	import type { CustomViewerConfig } from './types';

	let {
		config,
		projectId,
		apiBase,
		ref
	}: {
		config: CustomViewerConfig;
		projectId: string;
		apiBase: string;
		ref: string;
	} = $props();

	let loaded = $state(false);
	let error = $state('');

	function mountElement(node: HTMLElement) {
		node.setAttribute('repo-id', projectId);
		node.setAttribute('api-base', apiBase);
		node.setAttribute('ref', ref);
	}

	onMount(async () => {
		try {
			if (!customElements.get(config.tagName)) {
				const cacheBust = config.version ? `?v=${encodeURIComponent(config.version)}` : '';
				const url = `${config.scriptUrl}${cacheBust}`;
				// Dynamic runtime import of the custom element bundle
				await import(/* @vite-ignore */ url);
			}
			loaded = true;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load custom repository viewer bundle';
		}
	});
</script>

<div class="w-full">
	{#if error}
		<div
			class="flex items-center gap-3 rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive"
		>
			<AlertCircle class="h-5 w-5 shrink-0" />
			<div>
				<p class="font-semibold">Custom Viewer Error</p>
				<p class="text-xs opacity-90">{error}</p>
			</div>
		</div>
	{:else if !loaded}
		<div class="flex flex-col items-center justify-center gap-3 py-16 text-muted-foreground">
			<Loader2 class="h-6 w-6 animate-spin text-primary" />
			<p class="text-sm">Loading custom repository viewer ({config.tagName})…</p>
		</div>
	{:else}
		<!-- Dynamic Web Component Mount with action attributes -->
		<svelte:element this={config.tagName} use:mountElement class="block w-full" />
	{/if}
</div>
