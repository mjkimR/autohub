<script lang="ts">
	import { runHref } from '../pipeline-runs/run-links';
	import { NativeSelect } from '$lib/components/ui/native-select';
	import { Input } from '$lib/components/ui/input';
	import SddRunLinks from './SddRunLinks.svelte';
	import SddReadinessPreview from './SddReadinessPreview.svelte';
	import SddDiagnostics from '../pipeline-runs/SddDiagnostics.svelte';
	import { SddExecutionState } from './sdd-execution.svelte';
	import { Button } from '$lib/components/ui/button';
	import { untrack } from 'svelte';
	let {
		projectId,
		selectedSpec = '',
		repository = ''
	}: { projectId: string; selectedSpec?: string; repository?: string } = $props();
	const state = new SddExecutionState(() => projectId);
	$effect(() => {
		const project = projectId;
		const spec = selectedSpec;
		untrack(() => {
			state.selectProject(project);
			if (spec) state.spec = spec;
		});
	});
</script>

<section class="mb-4 space-y-3 rounded-lg border bg-card p-4">
	<h3 class="text-sm font-semibold">Run an SDD spec</h3>
	<p class="text-sm text-muted-foreground">
		Select a bound spec on an existing pull request whose head is the spec's activity branch (<code
			>dev-&lt;slug&gt;</code
		>). Execution checks the PR revision; the repository browser may show a different ref. For a new
		idea, prepare its spec and PR first; Work Plans do not create native SDD runs yet.
	</p>
	<div class="flex flex-wrap gap-3">
		<label class="min-w-64 flex-1 text-sm"
			>Unit directory (spec or proposal)
			<Input
				class="mt-1"
				bind:value={state.spec}
				placeholder="specs/2026-10/20261010-feature or docs/proposals/PROP-feature"
				disabled={state.busy}
			/>
		</label>
		<label class="text-sm"
			>Pull request
			<Input
				class="mt-1 w-28"
				type="number"
				min="1"
				bind:value={state.pull}
				disabled={state.busy}
			/>
		</label>
		<label class="text-sm"
			>Activity effort
			<NativeSelect
				class="mt-1 flex"
				bind:value={state.effort}
				disabled={state.busy}
				aria-label="Activity effort"
			>
				<option value="low">low</option>
				<option value="medium">medium</option>
				<option value="high">high</option>
			</NativeSelect>
		</label>
	</div>
	<div class="flex flex-wrap gap-2">
		<Button variant="outline" disabled={state.busy} onclick={() => state.checkRuntime()}
			>Check runtime</Button
		>
		<Button
			variant="outline"
			disabled={state.busy || !state.spec || !state.pull}
			onclick={() => state.inspect()}>Check readiness</Button
		>
		<Button disabled={!state.canStart} onclick={() => state.start()}>Start execution</Button>
	</div>
	{#if state.runId && state.startedKey === state.key()}<Button
			variant="outline"
			href={runHref(state.runId, projectId, 'decisions')}>Open execution & decisions</Button
		>{/if}
	<SddRunLinks {projectId} {repository} specDir={state.spec} refresh={state.runId} />
	{#if state.runtime}<p role="status" class="text-sm">{state.runtime}</p>{/if}
	{#if state.runtimeError}<p role="alert" class="text-sm text-destructive">
			{state.runtimeError}
		</p>{/if}
	{#if state.readiness?.ready}<SddReadinessPreview result={state.readiness} />{/if}
	{#if state.readiness}<SddDiagnostics
			diagnostics={state.readiness.diagnostics}
			warnings={state.readiness.warnings}
		/>{/if}
	{#if state.visibleMessage}<p role="status" class="text-sm">{state.visibleMessage}</p>{/if}
	{#if state.visibleError}<p role="alert" class="text-sm text-destructive">
			{state.visibleError}
		</p>{/if}
</section>
