<script lang="ts">
	import { untrack, tick } from 'svelte';
	import { Button } from '$lib/components/ui/button';
	import { NativeSelect } from '$lib/components/ui/native-select';
	import { Input } from '$lib/components/ui/input';
	import { Badge } from '$lib/components/ui/badge';
	import { runHref } from '../pipeline-runs/run-links';
	import { SddBatches } from './sdd-batches.svelte';
	let { projectId, selectedBatchId = '' }: { projectId: string; selectedBatchId?: string } =
		$props();
	const batches = new SddBatches();
	let batchId = $state('');
	$effect(() => {
		const project = projectId,
			id = selectedBatchId;
		untrack(() => {
			batches.reset(project);
			batchId = id;
			if (id) void batches.refresh(id);
			else batches.clear();
		});
	});
	$effect(() => {
		const id = batches.batch?.id;
		if (id)
			void tick().then(() => {
				if (batches.batch?.id !== id) return;
				const heading = document.getElementById(`sdd-batch-${id}`);
				heading?.focus({ preventScroll: true });
				heading?.scrollIntoView?.({ block: 'nearest' });
			});
	});
</script>

<section class="space-y-3 rounded-xl border bg-card p-4" aria-label="Retained SDD batches">
	<div class="flex flex-wrap items-center gap-2">
		<h3 class="mr-auto text-sm font-semibold">Retained SDD batches</h3>
		<Badge variant="outline">Retired · read only</Badge>
	</div>
	<p class="text-xs text-muted-foreground">
		Native milestone execution has been retired. These selections and outcomes are historical;
		opening them does not start or resume work.
	</p>
	<div class="flex flex-wrap items-end gap-2">
		<Button
			size="sm"
			variant="outline"
			disabled={batches.busy || batches.listBusy}
			onclick={() => batches.load(projectId)}>Load retained batches</Button
		>
		<label class="text-sm"
			>Batch ID<Input
				class="mt-1"
				bind:value={batchId}
				placeholder="Exact retained batch ID"
				disabled={batches.busy || batches.listBusy}
			/></label
		>
		<Button
			size="sm"
			variant="outline"
			disabled={batches.busy || !batchId.trim()}
			onclick={() => batches.refresh(batchId.trim())}>Open retained batch</Button
		>
	</div>
	{#if batches.rows.length}<label class="block text-sm"
			>Retained batches<NativeSelect
				class="mt-1 flex"
				aria-label="Retained batches"
				value={batches.batch?.id || ''}
				disabled={batches.busy || batches.listBusy}
				onchange={(event) => {
					batchId = event.currentTarget.value;
					void batches.refresh(batchId);
				}}
				><option value="">Choose batch</option>{#each batches.rows as row (row.id)}<option
						value={row.id}>{row.id} · {row.state}</option
					>{/each}</NativeSelect
			></label
		>{/if}
	{#if batches.busy}<p role="status" class="text-xs text-muted-foreground">
			Loading retained batch {batches.requestedId}…
		</p>{/if}
	{#if batches.listError}
		<div role="alert" class="space-y-2 text-sm">
			<p>{batches.listError}</p>
			<Button size="sm" variant="outline" onclick={() => batches.load(projectId)}
				>Retry retained list</Button
			>
		</div>
	{/if}
	{#if batches.error}<section role="alert" class="space-y-2 text-sm">
			<p>Batch unavailable: {batches.requestedId}. {batches.error}</p>
			{#if batches.requestedId}<Button size="sm" variant="outline" onclick={() => batches.refresh()}
					>Retry batch</Button
				>{/if}
			<Button size="sm" variant="outline" href={`/projects/${projectId}?tab=repository`}
				>Browse repository</Button
			>
		</section>{/if}
	{#if batches.batch}
		<h4 id={`sdd-batch-${batches.batch.id}`} tabindex="-1" class="text-xs break-all">
			Batch {batches.batch.id} · {batches.batch.state} · revision {batches.batch.revision}
		</h4>
		<Button size="sm" variant="outline" disabled={batches.busy} onclick={() => batches.refresh()}
			>Refresh status</Button
		>
		{#if batches.batch.detail}<p class="text-sm text-muted-foreground">
				{batches.batch.detail}
			</p>{/if}
		<ol class="space-y-2">
			{#each batches.batch.members as member, index (String(member.id || index))}<li
					class="space-y-1 rounded-lg border p-3 text-xs"
				>
					<p>
						{String(member.anchor_id || member.path || 'Retained member')} · {String(
							member.state || 'Recorded'
						)}
					</p>
					{#if member.run_id}<Button
							size="sm"
							variant="link"
							href={runHref(String(member.run_id), projectId)}>Open retained Run</Button
						>{/if}{#each Array.isArray(member.claims) ? member.claims : [] as claim, claimIndex (String(claim.id || claimIndex))}<p
						>
							{String(claim.activity || 'Activity')} · {claim.settled
								? 'Settled'
								: 'External ownership retained'}
							{#if claim.run_id}<Button
									size="sm"
									variant="link"
									href={runHref(String(claim.run_id), projectId)}>Open retained Run</Button
								>{/if}
						</p>{/each}
					<details>
						<summary class="cursor-pointer text-muted-foreground"
							>Recorded selection and outcome</summary
						>
						<pre class="mt-2 overflow-auto break-all whitespace-pre-wrap">{JSON.stringify(
								member,
								null,
								2
							)}</pre>
					</details>
				</li>{/each}
		</ol>
	{:else if !batches.busy}<p class="text-xs text-muted-foreground">
			Load the retained list or open an exact batch ID to inspect its history.
		</p>{/if}
</section>
