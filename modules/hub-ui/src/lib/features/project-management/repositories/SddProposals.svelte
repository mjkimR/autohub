<script lang="ts">
	import { api, type components } from '$lib/api';
	import { responseData } from '$lib/api/pagination';
	import { NativeSelect } from '$lib/components/ui/native-select';
	import { Input } from '$lib/components/ui/input';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import RunStateBadge from '../pipeline-runs/RunStateBadge.svelte';
	import { runHref } from '../pipeline-runs/run-links';
	import { sddStarts } from './sdd-starts.svelte';
	import SddStartOutcome from './SddStartOutcome.svelte';
	type Proposal = components['schemas']['ProposalState'];
	let { projectId, repository = '' }: { projectId: string; repository?: string } = $props();
	let base = $state('main');
	let effort = $state<'' | 'low' | 'medium' | 'high'>('');
	let items = $state<Proposal[]>([]);
	let truncated = $state(false);
	let loading = $state(false);
	let error = $state('');
	let starts = $derived(sddStarts(projectId));
	let generation = 0;
	const pullUrl = (n: number) => `https://github.com/${repository}/pull/${n}`;
	async function load() {
		const project = projectId,
			branch = base,
			requested = ++generation;
		loading = true;
		error = '';
		try {
			const result = responseData(
				await api.GET('/api/v1/projects/{project_id}/sdd/proposals', {
					params: { path: { project_id: project }, query: { base_branch: branch } }
				}),
				'Unable to list proposals'
			);
			if (requested !== generation || project !== projectId) return;
			items = result.items;
			truncated = !!result.truncated;
		} catch (e) {
			if (requested === generation)
				error = e instanceof Error ? e.message : 'Unable to list proposals';
		} finally {
			if (requested === generation) loading = false;
		}
	}
	async function start(item: Proposal, activity: 'plan' | 'dev') {
		await starts.activity(projectId, item.slug, activity, {
			request_id: crypto.randomUUID(),
			base_branch: base,
			...(effort ? { activity_effort: effort } : {})
		});
		if (!starts.pending) await load();
	}
	$effect(() => {
		if (projectId) void load();
	});
</script>

<section class="mb-4 space-y-3 rounded-lg border bg-card p-4" aria-label="Proposals">
	<div class="flex flex-wrap items-end gap-3">
		<h3 class="mr-auto text-sm font-semibold">Proposals</h3>
		<label class="text-sm"
			>Base branch<Input
				class="mt-1 w-36"
				bind:value={base}
				disabled={starts.busy || !!starts.pending}
			/></label
		>
		<label class="text-sm"
			>Activity effort<NativeSelect
				class="mt-1 flex"
				bind:value={effort}
				aria-label="Proposal activity effort"
				disabled={starts.busy || !!starts.pending}
				><option value="">Use repository recommendation</option><option value="low">low</option
				><option value="medium">medium</option><option value="high">high</option></NativeSelect
			></label
		>
		<Button variant="outline" disabled={loading} onclick={load}>Refresh proposals</Button>
	</div>
	<p class="text-xs text-muted-foreground">
		Choose the work to request. Both activities open Draft PRs. Proposal status is descriptive; the
		repository and agent own setup, prerequisites and workflow decisions.
	</p>
	{#if loading}<p role="status" class="text-sm text-muted-foreground">Loading proposals…</p>{/if}
	<ul class="divide-y">
		{#each items as item (item.slug)}
			<li class="space-y-2 py-3 text-sm">
				<div class="flex flex-wrap items-center gap-2">
					<span class="font-medium">{item.title}</span><code class="text-xs text-muted-foreground"
						>{item.id}</code
					><Badge variant="outline">{item.status}</Badge>
					{#if item.plan_pull}<Button size="sm" variant="link" href={pullUrl(item.plan_pull)}
							>Planning PR #{item.plan_pull}</Button
						>{/if}
					{#if item.dev_pull}<Button size="sm" variant="link" href={pullUrl(item.dev_pull)}
							>Development PR #{item.dev_pull}</Button
						>{/if}
					{#if item.run}<a href={runHref(item.run.id, projectId)} class="inline-flex"
							><span class="sr-only">PR run </span><RunStateBadge
								state={item.run.state as components['schemas']['PipelineRunState']}
							/></a
						>{/if}
				</div>
				{#if item.note}<p class="text-xs text-muted-foreground">{item.note}</p>{/if}
				<div class="flex flex-wrap gap-2">
					<Button
						size="sm"
						disabled={starts.busy || !!starts.pending}
						onclick={() => start(item, 'plan')}>Start Planning</Button
					><Button
						size="sm"
						variant="outline"
						disabled={starts.busy || !!starts.pending}
						onclick={() => start(item, 'dev')}>Start Development</Button
					>
				</div>
			</li>
		{/each}
	</ul>
	{#if !loading && !items.length && !error}<p class="text-sm text-muted-foreground">
			No proposals on {base}. Browse the repository or refresh after selecting another base.
		</p>{/if}
	{#if truncated}<p class="text-xs text-muted-foreground">Showing the first 50 proposals.</p>{/if}
	{#if starts.lastKind === 'activity'}<SddStartOutcome
			state={starts}
			{projectId}
			{repository}
		/>{/if}
	{#if error}<p role="alert" class="text-sm text-destructive">{error}</p>{/if}
</section>
