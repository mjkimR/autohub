<script lang="ts">
	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
	let { project }: { project: components['schemas']['ProjectRead'] } = $props();
	let runs = $state<components['schemas']['PipelineRunRead'][]>([]);
	let latestTests = $state<components['schemas']['ConnectionTestRead'][]>([]);
	let loading = $state(true);
	let error = $state('');
	function connectionStatus(test: components['schemas']['ConnectionTestRead']) {
		return !test.configuration_current
			? 'Retest recommended'
			: test.status === 'succeeded'
				? 'Verified'
				: test.status.replaceAll('_', ' ');
	}

	async function load() {
		try {
			const [runResult, testResult] = await Promise.all([
				api.GET('/api/v1/pipeline-runs', {
					params: { query: { project_id: project.id, limit: 5, offset: 0 } }
				}),
				api.GET('/api/v1/projects/{project_id}/connection-tests', {
					params: { path: { project_id: project.id } }
				})
			]);
			if (!runResult.data || !testResult.data) throw new Error('Could not load project activity');
			runs = runResult.data.items;
			const seen: string[] = [];
			latestTests = testResult.data.filter((test) => {
				const key = test.ai_catalog_id ?? 'legacy-codex';
				if (seen.includes(key)) return false;
				seen.push(key);
				return true;
			});
			error = '';
		} catch {
			error = 'Could not load project activity';
		} finally {
			loading = false;
		}
	}
	onMount(() => {
		void load();
	});
</script>

<div class="space-y-6">
	<div class="grid gap-4 sm:grid-cols-3">
		<a href="?tab=connections" class="rounded-xl border bg-card p-5 hover:border-primary/50"
			><p class="text-sm text-muted-foreground">AI connections</p>
			{#if loading || error}<p class="mt-2 text-sm">{loading ? 'Loading…' : 'Unavailable'}</p>
			{:else if !latestTests.length}<p class="mt-2 text-xl font-semibold">Not verified</p>
			{:else}
				{#each latestTests as test (test.id)}
					<p class="mt-2 text-sm">
						<span class="font-semibold">{test.catalog_snapshot?.name ?? 'Legacy Codex'}</span> · {connectionStatus(
							test
						)}
					</p>
				{/each}
			{/if}
		</a>

		<a href="?tab=automation" class="rounded-xl border bg-card p-5 hover:border-primary/50"
			><p class="text-sm text-muted-foreground">Automatic merge</p>
			<p class="mt-2 text-xl font-semibold">
				{project.github?.automation?.auto_merge ? 'Enabled' : 'Disabled'}
			</p>
			<p class="mt-2 text-xs text-muted-foreground">Connection tests are always excluded.</p></a
		>
		<a href="?tab=connections" class="rounded-xl border bg-card p-5 hover:border-primary/50"
			><p class="text-sm text-muted-foreground">GitHub / CI access</p>
			<p class="mt-2 text-xl font-semibold">
				{project.last_check?.ready
					? 'Checked'
					: project.last_check
						? 'Needs attention'
						: 'Unchecked'}
			</p>
			<p class="mt-2 text-xs text-muted-foreground">
				{project.github?.verification.workflow ?? 'Add a GitHub connection'}
			</p></a
		>
	</div>
	<section class="space-y-4 rounded-xl border bg-card p-6">
		<div class="flex items-center justify-between">
			<h2 class="text-lg font-semibold">Recent development runs</h2>
			<a href="?tab=runs" class="text-sm text-primary underline">All project runs</a>
		</div>
		{#if error}<p role="alert">
				{error} <button type="button" onclick={load} class="underline">Retry</button>
			</p>
		{:else if loading}<p class="text-sm text-muted-foreground">Loading activity…</p>
		{:else if runs.length === 0}<p class="text-sm text-muted-foreground">
				No development runs yet. Configure the connection, then enroll a PR in Runs.
			</p>
		{:else}<ul class="divide-y">
				{#each runs as run (run.id)}<li class="flex items-center justify-between gap-4 py-3">
						<a href={`?tab=runs&run=${run.id}`} class="text-sm text-primary underline"
							>PR #{run.pull_number} · {run.branch}</a
						><span class="text-sm">{run.state}</span>
					</li>{/each}
			</ul>{/if}
	</section>
</div>
