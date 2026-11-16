<script lang="ts">
	import { NativeSelect } from '$lib/components/ui/native-select';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import { untrack } from 'svelte';
	import SddRunLinks from './SddRunLinks.svelte';
	import SddStartOutcome from './SddStartOutcome.svelte';
	import { SddExecutionState } from './sdd-execution.svelte';
	let {
		projectId,
		selectedSpec = '',
		repository = '',
		contextual = false
	}: {
		projectId: string;
		selectedSpec?: string;
		repository?: string;
		contextual?: boolean;
	} = $props();
	const state = new SddExecutionState(() => projectId);
	$effect(() => {
		const spec = selectedSpec;
		untrack(() => {
			state.spec = spec;
		});
	});
</script>

<section class="space-y-3" aria-label="Run repository work">
	<p class="text-sm text-muted-foreground">
		Register an existing PR for this unit to follow its work in Hub.
	</p>
	<div class="flex flex-wrap gap-3">
		{#if !contextual}<label class="min-w-0 flex-1 text-sm"
				>Unit directory (spec or proposal)<Input
					class="mt-1"
					bind:value={state.spec}
					placeholder="specs/2026-11/20261113-feature"
					disabled={state.starts.busy || !!state.starts.pending}
				/></label
			>
		{/if}<label class="text-sm"
			>Pull request<Input
				class="mt-1 w-28"
				type="number"
				min="1"
				step="1"
				placeholder="PR number"
				bind:value={state.pull}
				disabled={state.starts.busy || !!state.starts.pending}
			/></label
		>
		<label class="text-sm"
			>Activity effort<NativeSelect
				class="mt-1 flex"
				bind:value={state.effort}
				disabled={state.starts.busy || !!state.starts.pending}
				aria-label="Activity effort"
				><option value="low">low</option><option value="medium">medium</option><option value="high"
					>high</option
				></NativeSelect
			></label
		>
	</div>
	<Button disabled={!state.canStart} onclick={() => state.start()}>Enroll PR</Button>
	{#if !contextual && state.starts.lastKind === 'enroll'}<SddStartOutcome
			state={state.starts}
			{projectId}
			{repository}
		/>{/if}
	{#if !contextual}<SddRunLinks
			{projectId}
			{repository}
			specDir={state.spec}
			refresh={state.starts.runId}
		/>{/if}
</section>
