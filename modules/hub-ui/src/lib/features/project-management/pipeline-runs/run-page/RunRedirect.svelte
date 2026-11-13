<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { Button } from '$lib/components/ui/button';
	import { runHref } from '../run-links';

	/** `/runs/<id>` resolves the run's project and replaces itself with the PR run page. */
	let { runId }: { runId: string } = $props();
	let problem = $state<'' | 'not-found' | 'error'>('');

	async function resolve() {
		problem = '';
		try {
			const res = await api.GET('/api/v1/pipeline-runs/{run_id}', {
				params: { path: { run_id: runId } }
			});
			if (!res.data) {
				problem = res.response?.status === 404 ? 'not-found' : 'error';
				return;
			}
			await goto(runHref(res.data.id, res.data.project_id) + window.location.hash, {
				replaceState: true
			});
		} catch {
			problem = 'error';
		}
	}
	onMount(() => {
		void resolve();
	});
</script>

<div class="mx-auto w-full max-w-7xl">
	{#if !problem}
		<p role="status" class="text-sm text-muted-foreground">Opening PR run…</p>
	{:else}
		<section class="space-y-3 rounded-xl border bg-card p-6">
			<h1 class="text-xl font-semibold">
				{problem === 'not-found' ? 'PR run not found' : 'PR run unavailable'}
			</h1>
			<p class="max-w-prose text-sm text-muted-foreground">
				{problem === 'not-found'
					? 'This PR run does not exist or its history has expired.'
					: 'The PR run could not be loaded. Check your connection and retry.'}
			</p>
			<div class="flex flex-wrap gap-2">
				{#if problem === 'error'}<Button onclick={resolve}>Retry</Button>{/if}
				<Button variant="outline" href="/projects/runs">All PR runs</Button>
			</div>
		</section>
	{/if}
</div>
