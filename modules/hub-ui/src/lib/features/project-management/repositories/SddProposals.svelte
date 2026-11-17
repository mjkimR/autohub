<script lang="ts">
	import WrapAtSeparators from '../pipeline-runs/WrapAtSeparators.svelte';
	import { untrack } from 'svelte';
	import { NativeSelect } from '$lib/components/ui/native-select';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import type { components } from '$lib/api';
	import { getRunStatePresentation } from '../pipeline-runs/presentation';
	import { runHref } from '../pipeline-runs/run-links';
	import { sddStarts } from './sdd-starts.svelte';
	import { ACTIVITY_LABELS, runOwesOperator, type UnitActivity } from './sdd-unit';
	let {
		projectId,
		unit,
		branch,
		active = {}
	}: {
		projectId: string;
		unit: string;
		branch: string;
		/** Non-final PR runs of this unit by activity; an owner demotes Start without blocking it. */
		active?: Partial<Record<UnitActivity, components['schemas']['PipelineRunRead']>>;
	} = $props();
	let base = $state(untrack(() => branch));
	let activity = $state<'plan' | 'dev'>('plan');
	let effort = $state<'' | 'low' | 'medium' | 'high'>('');
	const starts = $derived(sddStarts(projectId));
	const slug = $derived(unit.match(/^docs\/proposals\/PROP-([a-z0-9][a-z0-9_-]*)$/)?.[1]);
	const disabled = $derived(starts.busy || !!starts.pending);
	const owner = $derived(active[activity]);
	async function start() {
		if (!slug || !base.trim() || disabled) return;
		await starts.activity(projectId, slug, activity, {
			request_id: crypto.randomUUID(),
			base_branch: base.trim(),
			...(effort ? { activity_effort: effort } : {})
		});
	}
</script>

<form
	class="space-y-3"
	aria-label="SDD activity intent"
	onsubmit={(event) => {
		event.preventDefault();
		void start();
	}}
>
	<div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
		<label class="space-y-1 text-sm"
			><span class="font-medium">Activity</span>
			<NativeSelect class="flex w-full" bind:value={activity} {disabled}>
				<option value="plan">Planning</option><option value="dev">Development</option>
			</NativeSelect>
		</label>
		<label class="space-y-1 text-sm"
			><span class="font-medium">Activity base branch</span>
			<Input bind:value={base} {disabled} required />
		</label>
	</div>
	<details class="text-sm">
		<summary class="cursor-pointer text-muted-foreground">Activity preferences</summary>
		<label class="mt-3 block space-y-1"
			>Activity effort
			<NativeSelect
				class="flex w-full"
				bind:value={effort}
				{disabled}
				aria-label="Proposal activity effort"
			>
				<option value="">Use repository recommendation</option><option value="low">Low</option
				><option value="medium">Medium</option><option value="high">High</option>
			</NativeSelect>
		</label>
	</details>
	<div class="space-y-2 rounded-lg bg-muted/40 p-3">
		<p class="text-sm">
			<span class="font-medium">{activity === 'plan' ? 'Planning' : 'Development'}</span> · base
			<code class="break-words"><WrapAtSeparators text={base.trim() || 'Choose a branch'} /></code>
		</p>
		<p class="text-xs break-words text-muted-foreground"><WrapAtSeparators text={unit} /></p>
		{#if base.trim() !== branch}<p role="status" class="text-xs text-muted-foreground">
				This activity uses a different base from the document branch ({branch}).
			</p>{/if}
		<p class="text-xs text-muted-foreground">
			Creates a Draft PR and tracked Run. The agent follows the repository workflow.
		</p>
	</div>
	{#if owner}
		<div class="space-y-2 rounded-lg border p-3 text-sm">
			<p>
				PR #{owner.pull_number} ({getRunStatePresentation(owner.state).label}) already holds
				{ACTIVITY_LABELS[activity]} for this unit. Hub refuses another start while it is active.
			</p>
			<!-- An owed run's Open decisions in the unit status stays the single ink primary. -->
			<Button
				variant={runOwesOperator(owner) ? 'outline' : 'default'}
				href={runHref(owner.id, projectId)}>Open PR #{owner.pull_number}</Button
			>
		</div>
	{/if}
	<Button
		type="submit"
		variant={owner ? 'outline' : 'default'}
		disabled={disabled || !slug || !base.trim()}
		>{starts.busy
			? 'Starting activity…'
			: activity === 'plan'
				? 'Start Planning'
				: 'Start Development'}</Button
	>
</form>
