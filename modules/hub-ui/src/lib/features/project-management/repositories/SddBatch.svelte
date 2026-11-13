<script lang="ts">
	import { untrack } from 'svelte';
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
			disabled={batches.busy}
			onclick={() => batches.load(projectId)}>Load retained batches</Button
		>
		<label class="text-sm"
			>Batch ID<Input
				class="mt-1"
				bind:value={batchId}
				placeholder="Exact retained batch ID"
				disabled={batches.busy}
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
				disabled={batches.busy}
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
			Loading retained batch evidence…
		</p>{/if}
	{#if batches.error}<p role="alert" class="text-sm text-destructive">{batches.error}</p>{/if}
	{#if batches.batch}
		<p class="text-xs break-all">
			Batch {batches.batch.id} · {batches.batch.state} · revision {batches.batch.revision}
		</p>
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
