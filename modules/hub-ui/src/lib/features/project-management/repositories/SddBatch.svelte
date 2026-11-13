<script lang="ts">
	import { runHref } from '../pipeline-runs/run-links';
	import { NativeSelect } from '$lib/components/ui/native-select';
	import { untrack } from 'svelte';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import {
		SddBatches,
		executionOrder,
		selectable,
		type Preview,
		type Selection
	} from './sdd-batches.svelte';
	let {
		projectId,
		preview = null,
		onrefresh
	}: { projectId: string; preview?: Preview | null; onrefresh?: () => void } = $props();
	const batches = new SddBatches();
	let selected = $state<Selection[]>([]);
	let executionOpen = $state(false);
	const ordered = $derived(executionOrder(preview, selected));
	let confirm = $state<'create' | 'stop' | null>(null);
	$effect(() => {
		const project = projectId;
		untrack(() => batches.reset(project));
	});
	$effect(() => {
		void preview?.resolved_sha;
		batches.staleCreate = false;
		selected = [];
		executionOpen = false;
		confirm = null;
	});
	function inheritedEffort(id: string, key: 'planning_effort' | 'dev_effort') {
		return preview?.members.find((row) => row.id === id)?.[key] ?? 'medium';
	}
	function toggle(member: Preview['members'][number], checked: boolean) {
		if (!selectable(member) || !member.activity_kind || batches.pending) return;
		selected = checked
			? [...selected, { id: member.id, path: member.path, activity: member.activity_kind }]
			: selected.filter((row) => row.id !== member.id);
	}
	function preference(
		id: string,
		key: 'planning_effort' | 'dev_effort' | 'planning_catalog' | 'dev_catalog',
		value: string
	) {
		selected = selected.map((row) => (row.id === id ? { ...row, [key]: value || null } : row));
	}
</script>

<section class="space-y-3 rounded-xl border bg-card p-4" aria-label="SDD batch execution">
	<h3 class="font-semibold">Sequential milestone execution</h3>
	<Button
		variant="outline"
		disabled={batches.busy || Boolean(batches.pending)}
		onclick={() => batches.load(projectId)}>Load retained batches</Button
	>
	<p class="text-sm text-muted-foreground">
		Selection records intent through Development. Native approval, questions and PR merge remain
		separate.
	</p>
	{#if batches.error}<p role="alert">{batches.error}</p>{/if}
	{#if batches.pending}<p role="status">Request outcome unresolved. Keep the original request.</p>
		<Button disabled={batches.busy} onclick={() => batches.retry()}>Retry same request</Button>{/if}
	{#if batches.rows.length}
		<label
			>Retained batches <NativeSelect
				aria-label="Retained batches"
				disabled={batches.busy || Boolean(batches.pending)}
				onchange={(e) => batches.refresh(e.currentTarget.value)}
			>
				<option value="">Choose batch</option>{#each batches.rows as row (row.id)}<option
						value={row.id}>{row.id} · {row.state}</option
					>{/each}
			</NativeSelect></label
		>
	{/if}
	{#if batches.batch}
		<p>{batches.batch.id} · {batches.batch.state} · revision {batches.batch.revision}</p>
		<p>
			{batches.batch.members.length} selected · {batches.batch.members.filter(
				(m) => m.state === 'waiting'
			).length} waiting · {batches.batch.members.filter((m) => m.state === 'admitted').length} admitted
			· {batches.batch.members.filter((m) => m.state === 'succeeded').length} succeeded
		</p>
		<p class="break-all">
			Initial SHA: {String(batches.batch.basis.sha)} · Latest evaluation: {String(
				batches.batch.evaluation.sha ?? 'pending'
			)} · {String(batches.batch.evaluation.observed_at ?? '')}
		</p>
		<p>{batches.batch.detail ?? ''}</p>
		<ol class="list-decimal space-y-2 pl-5">
			{#each batches.batch.members as member, index (`${batches.batch.id}:${index}`)}
				<li>
					<strong>{String(member.anchor_id)}</strong> · {String(member.phase)} · {String(
						member.state
					)}
					<details>
						<summary>Inspect retained evidence and preferences</summary>
						<p>Original source: {String(member.path)}</p>
						<p>
							Current SPEC: {String(
								(member.spec_anchor as Record<string, unknown> | null)?.id ?? 'not yet established'
							)}
						</p>
						<p>
							Planning effort: {String(
								(
									(member.initial as Record<string, unknown>)?.preferences as Record<
										string,
										unknown
									>
								)?.planning_effort ?? 'inherited proposal default'
							)}
						</p>
						<p>
							Development effort: {String(
								(
									(member.initial as Record<string, unknown>)?.preferences as Record<
										string,
										unknown
									>
								)?.dev_effort ?? 'inherited proposal default'
							)}
						</p>
						<p>
							Planning catalog: {String(
								(
									(member.initial as Record<string, unknown>)?.preferences as Record<
										string,
										unknown
									>
								)?.planning_catalog ?? 'inherited project default'
							)}
						</p>
						<p>
							Development catalog: {String(
								(
									(member.initial as Record<string, unknown>)?.preferences as Record<
										string,
										unknown
									>
								)?.dev_catalog ?? 'inherited project default'
							)}
						</p>
						<p>
							Effective retained preferences: {Object.entries(
								((member.initial as Record<string, unknown>).effective_preferences as Record<
									string,
									unknown
								>) ?? {}
							)
								.map(([key, value]) => `${key.replaceAll('_', ' ')}: ${String(value)}`)
								.join(' · ')}
						</p>
						{#each (member.claims ?? []) as Record<string, unknown>[] as claim (String(claim.id))}
							<div class="space-y-1">
								{String(claim.activity)} · {claim.settled
									? 'Settled'
									: claim.uncertain
										? 'Outcome unknown — reconciliation required'
										: 'In flight'}
								{#if claim.uncertain}<p role="status">
										{String(
											claim.uncertainty_reason ??
												'Native admission response is uncertain. Retain this exact request.'
										)} · observed {String(claim.uncertainty_observed_at ?? 'time unavailable')}
									</p>{/if}
								{#if claim.run_id}<a
										class="underline"
										href={runHref(String(claim.run_id), projectId, 'decisions')}
										>Inspect native owner</a
									>{/if}
								{#if claim.pull_number}<a
										class="underline"
										href={`https://github.com/${String((batches.batch?.basis.project as Record<string, unknown>)?.repository)}/pull/${Number(claim.pull_number)}`}
										>PR #{String(claim.pull_number)}</a
									>{/if}
								{#if claim.branch}<span
										>Branch {String(claim.branch)} · initial commit {String(
											claim.initial_sha ?? 'not yet confirmed'
										)}</span
									>{/if}
							</div>
						{/each}
					</details>
				</li>{/each}
		</ol>
		<Button variant="outline" onclick={() => batches.refresh()}>Refresh status</Button>
		{#if !['stopped', 'completed'].includes(batches.batch.state)}
			<Button
				disabled={batches.busy || Boolean(batches.pending)}
				onclick={() => batches.control(batches.batch?.state === 'paused' ? 'resume' : 'pause')}
				>{batches.batch.state === 'paused' ? 'Resume' : 'Pause'} future admission</Button
			>
			<Button
				variant="outline"
				disabled={batches.busy || Boolean(batches.pending)}
				onclick={() => (confirm = 'stop')}>Stop future admission</Button
			>
		{/if}
		<p class="text-sm text-muted-foreground">
			Already admitted work may still create artifacts after pause or stop. Inspect its native owner
			for run controls.
		</p>
	{/if}
	{#if batches.staleCreate}<p role="alert">
			Selection basis changed. Refresh preview and review a new selection.
		</p>
		<Button onclick={() => onrefresh?.()}>Refresh execution preview</Button>{/if}
	{#if preview && !executionOpen}<Button
			disabled={!preview.complete}
			onclick={() => (executionOpen = true)}>Open execution selection</Button
		>{/if}
	{#if preview && executionOpen && !batches.staleCreate && !batches.rows.some((row) => row.exclusion)}
		<h4 class="font-medium">Execution selection</h4>
		<p class="text-sm break-all">
			{String(preview.milestone.id)} · {preview.requested_ref} · {preview.resolved_sha}
		</p>
		{#if !preview.complete}<p>Incomplete evidence; refresh preview before selecting.</p>{/if}
		<ul class="space-y-3">
			{#each preview.members as member, memberIndex (`${member.id}:${member.path}:${memberIndex}`)}
				<li class="space-y-2">
					<label
						><input
							type="checkbox"
							checked={selected.some((row) => row.id === member.id)}
							disabled={!preview.complete || !selectable(member) || Boolean(batches.pending)}
							onchange={(e) => toggle(member, e.currentTarget.checked)}
						/>
						{member.id} · {member.eligibility === 'eligible_now'
							? 'Eligible now'
							: 'Waiting future intent'}</label
					>
					<p class="text-sm">{member.reasons.join('; ')}</p>
					{#if selected.some((row) => row.id === member.id)}<div class="flex flex-wrap gap-2">
							{#each ['planning', 'dev'] as phase (phase)}
								<label
									>{phase} effort
									<NativeSelect
										aria-label={`${member.id} ${phase} effort`}
										onchange={(e) =>
											preference(
												member.id,
												phase === 'planning' ? 'planning_effort' : 'dev_effort',
												e.currentTarget.value
											)}
										><option value="">Inherit proposal default</option><option>low</option><option
											>medium</option
										><option>high</option></NativeSelect
									></label
								>
								<label
									>{phase} catalog <Input
										aria-label={`${member.id} ${phase} catalog`}
										placeholder="Inherit project default"
										onchange={(e) =>
											preference(
												member.id,
												phase === 'planning' ? 'planning_catalog' : 'dev_catalog',
												e.currentTarget.value
											)}
									/></label
								>
							{/each}
						</div>{/if}
				</li>{/each}
		</ul>
		<Button
			disabled={!ordered.length || !preview.complete || Boolean(batches.pending)}
			onclick={() => (confirm = 'create')}>Review selection</Button
		>
	{/if}
	{#if confirm}
		<div role="group" aria-label="Confirm future admission" class="space-y-2 rounded-md border p-3">
			{#if confirm === 'create'}<p>
					Confirm immutable selected intent through Planning and Development. Gates remain separate.
					Unselected prerequisites remain holds.
				</p>
				<ol>
					{#each ordered as row (row.id)}<li>
							{row.id} · {row.activity} · Planning effort: {row.planning_effort ??
								`inherited ${inheritedEffort(row.id, 'planning_effort')}`} · Development effort: {row.dev_effort ??
								`inherited ${inheritedEffort(row.id, 'dev_effort')}`} · Planning catalog: {row.planning_catalog ??
								'inherited project default'} · Development catalog: {row.dev_catalog ??
								'inherited project default'}
							<p>
								Current prerequisite holds: {preview?.members
									.find((m) => m.id === row.id)
									?.reasons.join('; ') || 'none observed'}
							</p>
						</li>{/each}
				</ol>
				<Button
					disabled={batches.busy}
					onclick={() => {
						confirm = null;
						if (preview) void batches.create(preview, ordered);
					}}>Confirm create</Button
				>
			{:else}<p>
					Stop permanently ends future admissions. Remaining members stay unexecuted; the admitted
					owner remains in flight.
				</p>
				<Button
					disabled={batches.busy}
					onclick={() => {
						confirm = null;
						void batches.control('stop');
					}}>Confirm stop</Button
				>{/if}
			<Button variant="outline" onclick={() => (confirm = null)}>Back</Button>
		</div>
	{/if}
</section>
