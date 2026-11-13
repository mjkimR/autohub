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
		repository = ''
	}: { projectId: string; selectedSpec?: string; repository?: string } = $props();
	const state = new SddExecutionState(() => projectId);
	$effect(() => {
		const spec = selectedSpec;
		untrack(() => {
			if (spec) state.spec = spec;
		});
	});
</script>

<section class="mb-4 space-y-3 rounded-lg border bg-card p-4" aria-label="Run repository work">
	<h3 class="text-sm font-semibold">Run repository work on an existing PR</h3>
	<p class="text-sm text-muted-foreground">
		The agent follows the repository's setup and workflow instructions. Hub tracks the PR, questions
		and GitHub checks. Repository readiness is not checked before starting.
	</p>
	<div class="flex flex-wrap gap-3">
		<label class="min-w-64 flex-1 text-sm"
			>Unit directory (spec or proposal)<Input
				class="mt-1"
				bind:value={state.spec}
				placeholder="specs/2026-11/20261113-feature"
				disabled={state.starts.busy || !!state.starts.pending}
			/></label
		>
		<label class="text-sm"
			>Pull request<Input
				class="mt-1 w-28"
				type="number"
				min="1"
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
	<Button disabled={!state.canStart} onclick={() => state.start()}>Start execution</Button>
	{#if state.starts.lastKind === 'enroll'}<SddStartOutcome
			state={state.starts}
			{projectId}
			{repository}
		/>{/if}
	<SddRunLinks {projectId} {repository} specDir={state.spec} refresh={state.starts.runId} />
</section>
