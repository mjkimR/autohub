<script lang="ts">
	import { untrack } from 'svelte';
	import { NativeSelect } from '$lib/components/ui/native-select';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import { sddStarts } from './sdd-starts.svelte';
	let { projectId, unit, branch }: { projectId: string; unit: string; branch: string } = $props();
	let base = $state(untrack(() => branch));
	let activity = $state<'plan' | 'dev'>('plan');
	let effort = $state<'' | 'low' | 'medium' | 'high'>('');
	const starts = $derived(sddStarts(projectId));
	const slug = $derived(unit.match(/^docs\/proposals\/PROP-([a-z0-9][a-z0-9_-]*)$/)?.[1]);
	const disabled = $derived(starts.busy || !!starts.pending);
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
	<div class="grid gap-3 sm:grid-cols-2">
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
			<code class="break-all">{base.trim() || 'Choose a branch'}</code>
		</p>
		<p class="text-xs break-all text-muted-foreground">{unit}</p>
		{#if base.trim() !== branch}<p role="status" class="text-xs text-muted-foreground">
				This activity uses a different base from the document branch ({branch}).
			</p>{/if}
		<p class="text-xs text-muted-foreground">
			Creates a Draft PR and tracked Run. The agent follows the repository workflow.
		</p>
	</div>
	<Button type="submit" disabled={disabled || !slug || !base.trim()}
		>{starts.busy
			? 'Starting activity…'
			: activity === 'plan'
				? 'Start Planning'
				: 'Start Development'}</Button
	>
</form>
