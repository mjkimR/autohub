<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { components } from '$lib/api';
	import { displayLabel } from '$lib/labels';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { MessageSquare } from '@lucide/svelte';
	import WrapAtSeparators from '../../pipeline-runs/WrapAtSeparators.svelte';
	import RunStateBadge from '../../pipeline-runs/RunStateBadge.svelte';
	import RunDraftBadge from '../../pipeline-runs/RunDraftBadge.svelte';
	import { runHref } from '../../pipeline-runs/run-links';
	import { ACTIVITY_LABELS, runOwesOperator } from '../sdd-unit';
	import { groupSummary, isOpenMilestone, progressGroups } from './progress';
	import type { RepositoryDocument } from './model';
	/**
	 * Units on the branch grouped by milestone, each with its document status and latest PR run per
	 * activity. Descriptive only: it opens documents and runs and never starts work
	 * (CAP-DOC-repository-viewer rule 10).
	 */
	let {
		documents,
		onopen,
		runs = null,
		projectId = '',
		status,
		openMilestonesOnly = false
	}: {
		documents: RepositoryDocument[];
		onopen: (path: string) => void;
		/** PR runs by unit; null while unavailable, so rows show document status only. */
		runs?: Map<string, components['schemas']['PipelineRunRead'][]> | null;
		projectId?: string;
		/** Loading, error or truncation notice for the PR runs. */
		status?: Snippet;
		/** Only open milestones and their members, as on the project's Milestones tab. */
		openMilestonesOnly?: boolean;
	} = $props();
	const groups = $derived(
		progressGroups(documents, runs ?? new Map()).filter(
			(group) => !openMilestonesOnly || (group.milestone && isOpenMilestone(group.milestone))
		)
	);
	const statusLabel = (value: string) => displayLabel(value || 'unknown');
</script>

<div class="space-y-4">
	<p class="text-xs text-muted-foreground">
		Statuses come from repository documents and Hub's PR runs. They do not decide readiness or order
		work, and opening a unit does not start it.
	</p>
	{@render status?.()}
	{#if !groups.length}<p class="text-sm text-muted-foreground">
			{openMilestonesOnly
				? 'No open milestones on this branch. Planned and active milestones in docs/roadmap/ appear here.'
				: 'No milestones, proposals or specs on the selected branch.'}
		</p>{/if}
	{#each groups as group (group.key)}
		<section class="space-y-2 rounded-lg border p-3" aria-label={group.title}>
			<div class="space-y-1">
				<div class="flex flex-wrap items-center gap-2">
					{#if group.milestone}{@const milestone = group.milestone}
						<h3 class="text-sm font-semibold">
							<button
								type="button"
								class="inline-flex min-h-6 items-center text-left underline-offset-4 hover:underline"
								onclick={() => onopen(milestone.path)}>{group.title}</button
							>
						</h3>
						<Badge variant="outline">{statusLabel(milestone.status)}</Badge>
					{:else}<h3 class="text-sm font-semibold">{group.title}</h3>{/if}
				</div>
				<p class="text-xs text-muted-foreground">{groupSummary(group.rows)}</p>
				{#if group.dependencies.length}<p class="text-xs">
						Depends on: {group.dependencies
							.map((dependency) => `${dependency.id} (${statusLabel(dependency.status)})`)
							.join(', ')}
					</p>{/if}
				{#if group.key === 'specs' && groups.some((g) => g.milestone)}<p
						class="text-xs text-muted-foreground"
					>
						Proposals that finished Development may leave their milestone; their specs are listed
						here.
					</p>{/if}
			</div>
			{#if !group.rows.length}<p class="text-sm text-muted-foreground">
					No direct proposal members.
				</p>{/if}
			<ul class="divide-y">
				{#each group.rows as row (row.document.path)}<li class="space-y-1 py-2">
						<div class="flex flex-wrap items-center gap-x-2 gap-y-1">
							<button
								type="button"
								class="inline-flex min-h-6 items-center text-left text-sm font-medium underline-offset-4 hover:underline"
								onclick={() => onopen(row.document.path)}>{row.document.title}</button
							>
							<Badge variant="outline"
								><span class="sr-only">Document status:</span>{statusLabel(
									row.document.status
								)}</Badge
							>
						</div>
						<p class="font-mono text-xs break-words text-muted-foreground">
							<WrapAtSeparators text={row.unit} />
						</p>
						{#each row.runs as { activity, run } (run.id)}
							<div class="flex flex-wrap items-center gap-2 text-xs">
								<span>{activity ? ACTIVITY_LABELS[activity] : 'PR run'}</span>
								{#if projectId}<a
										class="inline-flex min-h-6 items-center underline underline-offset-4"
										href={runHref(run.id, projectId)}
										aria-label={`Open PR run for PR #${run.pull_number}`}>PR #{run.pull_number}</a
									>{:else}<span>PR #{run.pull_number}</span>{/if}
								<RunStateBadge state={run.state} />
								<RunDraftBadge {run} />
								{#if projectId && runOwesOperator(run)}<Button
										size="sm"
										variant="outline"
										href={runHref(run.id, projectId, 'decisions')}
										><MessageSquare aria-hidden="true" />Open decisions<span class="sr-only">
											for PR #{run.pull_number}</span
										></Button
									>{/if}
							</div>
						{/each}
					</li>{/each}
			</ul>
		</section>
	{/each}
</div>
