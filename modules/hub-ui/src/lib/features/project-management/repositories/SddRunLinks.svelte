<script lang="ts">
	import WrapAtSeparators from '../pipeline-runs/WrapAtSeparators.svelte';
	import { api, type components } from '$lib/api';
	import { responseData } from '$lib/api/pagination';
	import RunStateBadge from '../pipeline-runs/RunStateBadge.svelte';
	import RunDraftBadge from '../pipeline-runs/RunDraftBadge.svelte';
	import { unitRunHref } from './sdd-unit';
	const LIMIT = 20;
	let {
		projectId,
		specDir,
		refresh = '',
		repository = '',
		runs = $bindable([])
	}: {
		projectId: string;
		specDir: string;
		refresh?: string;
		repository?: string;
		/** The unit's PR runs, newest first; bind it to summarise them elsewhere in the panel. */
		runs?: components['schemas']['PipelineRunRead'][];
	} = $props();
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
		const valid =
			/^(specs\/\d{4}-\d{2}\/[a-zA-Z0-9_-]+|docs\/proposals\/PROP-[a-zA-Z0-9_-]+)$/.test(spec);
		loading = valid;
		if (!valid) return;
		let active = true;
		const timer = setTimeout(async () => {
			try {
				const result = responseData(
					await api.GET('/api/v1/projects/{project_id}/sdd/runs', {
						params: { path: { project_id: project }, query: { spec_dir: spec } }
					}),
					''
				);
				if (active) runs = result;
			} catch {
				if (active) error = "Couldn't load PR runs for this unit.";
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
	<div class="space-y-2">
		{#if loading}<p role="status" class="text-xs text-muted-foreground">Loading PR runs…</p>
		{:else if error}<p role="alert" class="text-xs text-destructive">
				{error}
				<button
					type="button"
					class="inline-flex min-h-6 items-center underline underline-offset-4"
					onclick={() => {
						retry += 1;
					}}>Retry history</button
				>
			</p>
		{:else if !runs.length}<p class="text-xs text-muted-foreground">
				No PR runs for this unit yet. {specDir.startsWith('docs/proposals/')
					? 'Start Planning or Development, or enroll an existing PR.'
					: 'Enroll an existing PR to follow its work in Hub.'}
			</p>
		{:else}
			<ul class="space-y-2">
				{#each runs as run (run.id)}<li>
						<a
							class="flex flex-wrap items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-muted"
							href={unitRunHref(run, projectId)}
						>
							<span class="font-medium">PR #{run.pull_number}</span>
							<RunStateBadge state={run.state} />
							<RunDraftBadge {run} />
							<span class="min-w-0 break-words">{run.pull_snapshot.title}</span>
						</a>
						<p class="mt-1 text-xs break-words text-muted-foreground">
							{#if run.sdd_snapshot?.handoff_from}<WrapAtSeparators
									text={String(run.sdd_snapshot.handoff_from)}
								/> →
							{/if}<WrapAtSeparators text={String(run.sdd_snapshot?.spec_dir || specDir)} />
						</p>
						{#if /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repository)}
							<a
								class="inline-flex min-h-6 items-center text-xs underline underline-offset-4"
								href={`https://github.com/${repository}/pull/${run.pull_number}`}
								target="_blank"
								rel="noreferrer">Open GitHub PR #{run.pull_number}</a
							>
						{/if}
					</li>{/each}
			</ul>
			{#if runs.length >= LIMIT}<p class="text-xs text-muted-foreground">
					Showing the latest {LIMIT} PR runs.
				</p>{/if}
		{/if}
	</div>
{/if}
