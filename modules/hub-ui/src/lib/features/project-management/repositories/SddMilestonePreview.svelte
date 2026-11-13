<script lang="ts">
	import { NativeSelect } from '$lib/components/ui/native-select';
	import SddBatch from './SddBatch.svelte';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { Button } from '$lib/components/ui/button';
	import { orderedSelection, type MilestonePreview } from './milestone-selection';

	let {
		projectId,
		repository,
		currentRef,
		refresh = 0
	}: {
		projectId: string;
		repository: string;
		currentRef: string;
		refresh?: number;
	} = $props();
	let milestones = $state<components['schemas']['MilestoneList'] | null>(null);
	let milestone = $state('');
	let preview = $state<MilestonePreview | null>(null);
	let selected = $state<string[]>([]);
	let error = $state('');
	let loading = $state(false);
	let listing = $state(false);
	let requestRevision = 0;
	let controller: AbortController | null = null;
	const order = $derived(orderedSelection(preview, selected));

	function invalidate() {
		requestRevision++;
		controller?.abort();
		preview = null;
		selected = [];
		error = '';
		loading = false;
	}

	$effect(() => {
		const project = projectId,
			ref = currentRef;
		void refresh;
		invalidate();
		milestone = '';
		milestones = null;
		listing = Boolean(ref);
		const request = new AbortController();
		let active = true;
		if (ref)
			void (async () => {
				try {
					const response = await api.GET('/api/v1/projects/{project_id}/sdd/milestones', {
						params: { path: { project_id: project }, query: { ref } },
						signal: request.signal
					});
					if (!active) return;
					if (!response.data)
						throw new Error(apiErrorMessage(response.error, 'Could not list milestones'));
					milestones = response.data;
				} catch (e) {
					if (active) error = e instanceof Error ? e.message : 'Could not list milestones';
				} finally {
					if (active) listing = false;
				}
			})();
		return () => {
			active = false;
			request.abort();
			invalidate();
		};
	});

	async function inspect() {
		invalidate();
		if (!milestone || !currentRef) return;
		const revision = requestRevision;
		controller = new AbortController();
		loading = true;
		try {
			const response = await api.POST('/api/v1/projects/{project_id}/sdd/milestone-preview', {
				params: { path: { project_id: projectId } },
				body: { ref: currentRef, milestone_id: milestone },
				signal: controller.signal
			});
			if (revision !== requestRevision) return;
			if (!response.data)
				throw new Error(apiErrorMessage(response.error, 'Could not preview milestone'));
			preview = response.data;
		} catch (e) {
			if (revision === requestRevision)
				error = e instanceof Error ? e.message : 'Could not preview milestone';
		} finally {
			if (revision === requestRevision) loading = false;
		}
	}

	function toggle(id: string, checked: boolean) {
		if (
			!preview?.complete ||
			!preview.members.some((m) => m.id === id && m.eligibility === 'eligible_now')
		)
			return;
		selected = checked ? [...new Set([...selected, id])] : selected.filter((value) => value !== id);
	}

	function source(path: string) {
		return `https://github.com/${repository}/blob/${preview?.resolved_sha}/${path.split('/').map(encodeURIComponent).join('/')}`;
	}
</script>

<section class="space-y-4 rounded-xl border bg-card p-4 shadow-xs" aria-label="Milestone preview">
	<h3 class="font-semibold">Preview milestone work</h3>
	<p class="text-sm text-muted-foreground">
		{repository} · {currentRef || 'Choose a branch'}. Review only; no activities start and no queue
		is saved.
	</p>
	<div class="flex flex-wrap items-center gap-3">
		<label class="text-sm"
			>Milestone
			<NativeSelect
				aria-label="Milestone"
				value={milestone}
				disabled={listing || !milestones?.complete}
				class="ml-2"
				onchange={(event) => {
					invalidate();
					milestone = event.currentTarget.value;
				}}
			>
				<option value="">Choose a milestone</option>
				{#each milestones?.items ?? [] as item, index (`${String(item.id)}:${String(item.path)}:${index}`)}
					<option value={String(item.id)}
						>{String(item.id)} · {String(item.title)} · {String(item.status)}</option
					>
				{/each}
			</NativeSelect>
		</label>
		<Button variant="outline" disabled={!milestone || loading} onclick={inspect}
			>Preview milestone</Button
		>
		<Button variant="outline" disabled={!milestone} onclick={inspect}>Refresh preview</Button>
	</div>
	{#if listing}<p role="status">Loading milestones…</p>{/if}
	{#if milestones && !milestones.complete}<p role="alert">
			Milestone catalog incomplete: {milestones.reasons.join('; ')}. Refresh the repository to
			retry.
		</p>{/if}
	{#if milestones?.complete && !milestones.items.length}<p>
			No milestones found. Choose another branch or refresh the repository.
		</p>{/if}
	{#if loading}<p role="status">Previewing {milestone} on {currentRef}…</p>{/if}
	{#if error}<p role="alert" class="text-destructive">{error}</p>{/if}
	{#if preview}
		<div class="space-y-1 text-sm">
			<p class="break-all">Captured SHA: <code>{preview.resolved_sha || 'unavailable'}</code></p>
			<p>
				{String(preview.milestone.id)} · {String(preview.milestone.path ?? '')} · {String(
					preview.milestone.status ?? 'unknown'
				)}
			</p>
			<p>Repository observation: {preview.observed_at}</p>
			<p>
				Members {preview.counts.members}/{preview.limits.members} · prerequisite anchors {preview
					.counts.anchors}/{preview.limits.anchors} · edges {preview.counts.edges}/{preview.limits
					.edges} · deadline {preview.limits.deadline_seconds}s
			</p>
		</div>
		{#if !preview.complete}<div role="alert" class="text-sm text-destructive">
				Incomplete preview. Selection and order are disabled.
				<ul>
					{#each preview.reasons as reason, index (index)}<li>{reason}</li>{/each}
				</ul>
			</div>{/if}
		{#if !preview.members.length}<p>
				No direct proposal members observed. Choose another milestone or refresh; this does not
				establish completed delivery.
			</p>{/if}
		<div class="overflow-x-auto">
			<table class="w-full text-left text-sm">
				<caption class="sr-only">Milestone member readiness at captured SHA</caption>
				<thead
					><tr
						><th>Select</th><th>Proposal</th><th>Activity</th><th>Readiness</th><th>Evidence</th
						></tr
					></thead
				>
				<tbody
					>{#each preview.members as member, index (`${member.id}:${member.path}:${index}`)}
						<tr class="border-t align-top">
							<td class="py-2"
								><input
									type="checkbox"
									aria-label={`Select ${member.id}`}
									checked={selected.includes(member.id)}
									disabled={!preview.complete || member.eligibility !== 'eligible_now'}
									onchange={(e) => toggle(member.id, e.currentTarget.checked)}
								/></td
							>
							<td class="p-2"
								><a class="underline" href={source(member.path)} target="_blank" rel="noreferrer"
									>{member.id}</a
								>
								<p>{member.title}</p></td
							>
							<td class="p-2"
								>{member.activity_kind === 'plan'
									? 'Planning'
									: member.activity_kind === 'dev'
										? 'Handoff-first Development'
										: 'Inspection only'}
								<p>{member.stage ?? ''}</p></td
							>
							<td class="p-2"
								>{member.eligibility.replaceAll('_', ' ')}
								<p>Admission: {member.admission}; scheduling: {member.scheduling}</p></td
							>
							<td class="p-2"
								><details>
									<summary>Inspect prerequisites and evidence</summary>
									<ul>
										{#each member.reasons as reason, index (index)}<li>{reason}</li>{/each}
									</ul>
									{#each preview.edges.filter((edge) => edge.source === member.id || edge.source === preview?.milestone.id) as edge, index (index)}
										<p>
											{String(edge.source)} → {String(edge.requested_id)} → {String(
												edge.canonical_id ?? 'unresolved'
											)} · {String(edge.status)}
											{#if edge.path}<a
													class="underline"
													href={source(String(edge.path))}
													target="_blank"
													rel="noreferrer">{String(edge.path)}</a
												>{/if}
										</p>
									{/each}
									<pre class="max-w-sm overflow-auto text-xs">{JSON.stringify(
											member.workflow_hold,
											null,
											2
										)}</pre>
									<p>Runtime: {preview.runtime_identity ?? 'unavailable'}</p>
									{#each member.evidence as evidence, index (index)}<p>
											{#if evidence.run_id}<a
													class="underline"
													href={`/projects/runs?run=${encodeURIComponent(String(evidence.run_id))}&view=decisions`}
													>Inspect run {String(evidence.run_id)}</a
												> ·
											{/if}
											<a
												class="underline"
												href={`https://github.com/${repository}/pull/${Number(evidence.pull_number)}`}
												target="_blank"
												rel="noreferrer">Inspect PR #{String(evidence.pull_number)}</a
											>
											· head {String(evidence.head_sha ?? 'unknown')} · base {String(
												evidence.base_sha ?? 'unknown'
											)}
										</p>{/each}
									{#if member.evidence_observed_at}<p>
											External execution observation: {member.evidence_observed_at}. Separate from
											repository snapshot.
										</p>{/if}
								</details></td
							>
						</tr>
					{/each}</tbody
				>
			</table>
		</div>
		{#each preview.warnings as warning, index (index)}<p role="status" class="text-sm">
				{warning.code}: {warning.detail}
			</p>{/each}
		{#if preview.complete}
			<div class="space-y-2 border-t pt-3" aria-label="Selected activities">
				<h4 class="font-medium">Selected activities ({order.length})</h4>
				<p class="text-sm text-muted-foreground">
					Suggested order for this explicit subset. Unfinished prerequisites remain held. Later
					execution requires fresh admission.
				</p>
				<ol>
					{#each order as member (member.id)}<li>
							{member.id} · {member.activity_kind === 'plan'
								? 'Planning'
								: 'Handoff-first Development'}
						</li>{/each}
				</ol>
				<Button variant="outline" disabled={!selected.length} onclick={() => (selected = [])}
					>Clear selection</Button
				>
			</div>
		{/if}
	{/if}
</section>

<SddBatch {projectId} {preview} onrefresh={inspect} />
