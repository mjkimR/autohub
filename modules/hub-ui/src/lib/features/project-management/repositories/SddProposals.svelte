<script lang="ts">
	import { SvelteMap } from 'svelte/reactivity';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { Button } from '$lib/components/ui/button';
	type Proposal = components['schemas']['ProposalState'];
	let { projectId, repository = '' }: { projectId: string; repository?: string } = $props();
	let base = $state('main');
	let effort = $state<'low' | 'medium' | 'high'>('medium');
	let items = $state<Proposal[]>([]);
	let truncated = $state(false);
	let loading = $state(false);
	let busy = $state('');
	let error = $state('');
	let message = $state('');
	let rejecting = $state('');
	let reason = $state('');
	// One request id per intent, reused when a lost response is retried.
	const ids = new SvelteMap<string, string>();
	const idFor = (intent: string) =>
		ids.get(intent) ?? ids.set(intent, crypto.randomUUID()).get(intent)!;
	const pullUrl = (n: number) => `https://github.com/${repository}/pull/${n}`;
	async function load() {
		loading = true;
		error = '';
		try {
			const result = await api.GET('/api/v1/projects/{project_id}/sdd/proposals', {
				params: { path: { project_id: projectId }, query: { base_branch: base } }
			});
			if (result.error) throw new Error(apiErrorMessage(result.error, 'Unable to list proposals'));
			items = result.data?.items ?? [];
			truncated = !!result.data?.truncated;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unable to list proposals';
		} finally {
			loading = false;
		}
	}
	async function act(item: Proposal, action: Proposal['actions'][number]) {
		busy = item.slug;
		error = '';
		message = '';
		try {
			if (action === 'start_planning' || action === 'start_development') {
				const path =
					action === 'start_planning'
						? '/api/v1/projects/{project_id}/sdd/proposals/{slug}/planning'
						: '/api/v1/projects/{project_id}/sdd/proposals/{slug}/development';
				const result = await api.POST(path, {
					params: { path: { project_id: projectId, slug: item.slug } },
					body: {
						request_id: idFor(`${action}:${item.slug}:${base}`),
						base_branch: base,
						activity_effort: effort
					}
				});
				if (result.error) throw new Error(apiErrorMessage(result.error, 'Could not start'));
				message = `${item.id}: ${action === 'start_planning' ? 'Planning' : 'Development'} started.`;
			} else if (item.run) {
				const decision = action === 'accept' ? 'accept_plan' : 'reject_plan';
				const note = action === 'reject' ? reason : '';
				const run = item.run;
				const result = await api.POST('/api/v1/pipeline-runs/{run_id}/resume', {
					params: { path: { run_id: run.id } },
					body: {
						request_id: idFor(JSON.stringify([run.id, run.revision, decision, note])),
						expected_revision: run.revision,
						decision,
						head_sha: run.head_sha ?? '',
						feedback: note
					}
				});
				if (result.error)
					throw new Error(apiErrorMessage(result.error, 'Decision was not applied'));
				message = `${item.id}: ${action === 'accept' ? 'accepted' : 'rejected'}; the pull request merges by policy.`;
				rejecting = '';
				reason = '';
			}
			await load();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Action failed';
		} finally {
			busy = '';
		}
	}
	$effect(() => {
		if (projectId) void load();
	});
</script>

<section class="mb-4 space-y-3 rounded-lg border bg-card p-4" aria-label="Proposals">
	<div class="flex flex-wrap items-end gap-3">
		<h3 class="mr-auto text-sm font-semibold">Proposals</h3>
		<label class="text-sm"
			>Base branch
			<input class="mt-1 block w-36 rounded border bg-background p-2" bind:value={base} />
		</label>
		<label class="text-sm"
			>Activity effort
			<select
				class="mt-1 block rounded border bg-background p-2"
				bind:value={effort}
				aria-label="Proposal activity effort"
			>
				<option value="low">low</option><option value="medium">medium</option><option value="high"
					>high</option
				>
			</select>
		</label>
		<Button variant="outline" disabled={loading} onclick={load}>Refresh</Button>
	</div>
	{#if loading}<p role="status" class="text-sm text-muted-foreground">Loading proposals…</p>{/if}
	<ul class="divide-y">
		{#each items as item (item.slug)}
			<li class="space-y-2 py-3 text-sm">
				<div class="flex flex-wrap items-center gap-2">
					<span class="font-medium">{item.title}</span>
					<code class="text-xs text-muted-foreground">{item.id}</code>
					<span class="rounded border px-2 text-xs">{item.display_status}</span>
					{#if item.plan_pull}<a class="text-xs underline" href={pullUrl(item.plan_pull)}
							>plan-{item.slug} #{item.plan_pull}</a
						>{/if}
					{#if item.dev_pull}<a class="text-xs underline" href={pullUrl(item.dev_pull)}
							>dev-{item.slug} #{item.dev_pull}</a
						>{/if}
					{#if item.run}<span class="text-xs text-muted-foreground">run {item.run.state}</span>{/if}
				</div>
				{#if item.note}<p class="text-xs text-muted-foreground">{item.note}</p>{/if}
				<div class="flex flex-wrap gap-2">
					{#each item.actions as action (action)}
						{#if action === 'reject'}
							<Button
								size="sm"
								variant="outline"
								disabled={!!busy}
								onclick={() => (rejecting = rejecting === item.slug ? '' : item.slug)}
								>Reject…</Button
							>
						{:else}
							<Button size="sm" disabled={!!busy} onclick={() => void act(item, action)}
								>{action === 'start_planning'
									? 'Start review'
									: action === 'start_development'
										? 'Start development'
										: 'Accept'}</Button
							>
						{/if}
					{/each}
				</div>
				{#if rejecting === item.slug}
					<div class="space-y-2">
						<label class="block text-sm"
							>Rejection reason (kept in the commit message)
							<textarea
								class="mt-1 min-h-16 w-full rounded border bg-background p-2"
								bind:value={reason}
								maxlength="8000"></textarea>
						</label>
						<Button
							size="sm"
							variant="destructive"
							disabled={!!busy || !reason.trim()}
							onclick={() => void act(item, 'reject')}>Reject proposal</Button
						>
					</div>
				{/if}
			</li>
		{/each}
	</ul>
	{#if !loading && !items.length && !error}<p class="text-sm text-muted-foreground">
			No proposals on {base}.
		</p>{/if}
	{#if truncated}<p class="text-xs text-muted-foreground">Showing the first 50 proposals.</p>{/if}
	{#if message}<p role="status" class="text-sm">{message}</p>{/if}
	{#if error}<p role="alert" class="text-sm text-destructive">{error}</p>{/if}
</section>
