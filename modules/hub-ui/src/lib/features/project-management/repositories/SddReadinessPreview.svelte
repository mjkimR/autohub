<script lang="ts">
	import type { components } from '$lib/api';
	import { Badge } from '$lib/components/ui/badge';
	let { result }: { result: components['schemas']['SddReadiness'] } = $props();
	const record = (value: unknown): Record<string, unknown> =>
		value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
	const rows = (value: unknown) => (Array.isArray(value) ? value.map(record).slice(0, 10) : []);
	let current = $derived(record(result.current));
	let stage = $derived(record(current.stage));
	let questions = $derived(rows(current.pending_questions));
	let problems = $derived(rows(current.problems));
	let malformed = $derived(rows(current.malformed_workers));
	let requests = $derived(rows(current.requests));
	let policy = $derived(record(record(result.policy).approvals));
	let activeGate = $derived(
		typeof stage.human_gate === 'string' && record(policy[stage.human_gate]).policy !== 'auto'
			? stage.human_gate
			: ''
	);
	let held = $derived(Boolean(current.blocked) || questions.length > 0 || malformed.length > 0);
	let waiting = $derived(held || requests.length > 0 || Boolean(activeGate));
	let approvals = $derived(Object.entries(policy));
</script>

<section class="space-y-3 rounded-lg border bg-muted/20 p-4" aria-label="Execution preview">
	<div class="flex flex-wrap items-center justify-between gap-2">
		<h4 class="text-sm font-semibold">Execution preview</h4>
		<Badge variant="outline">Eligible to register</Badge>
	</div>
	<p class="text-xs break-all text-muted-foreground">
		Inspected commit {result.head_sha?.slice(0, 12)} · {result.cli_version}
	</p>
	<dl class="space-y-1 text-sm">
		<div class="flex flex-wrap gap-x-2">
			<dt class="text-muted-foreground">Next stage</dt>
			<dd class="font-medium">
				{current.complete
					? 'Workflow complete'
					: String(stage.name || stage.id || 'No next stage reported')}
			</dd>
		</div>
	</dl>
	{#if waiting}
		<div class="space-y-2 rounded-lg border p-3 text-sm">
			<p class="font-medium">Workflow input reported</p>
			{#if current.blocked}<p>Worker evidence blocks progress.</p>{/if}
			{#each problems as problem, index (index)}
				<p class="break-words">
					Problem: {String(problem.cause || problem.file || 'Unresolved worker problem')}
				</p>
			{/each}
			{#each malformed as worker, index (index)}
				<p class="break-words">
					Invalid worker report: {String(worker.reason || worker.file || 'Repair required')}
				</p>
			{/each}
			{#each questions as question, index (index)}
				<p class="break-words">
					Question: {String(question.title || question.id || 'Answer required')}
				</p>
			{/each}
			{#each requests as request, index (index)}
				<p class="break-words">
					{request.kind === 'approve' ? 'Approval requested' : 'Workflow request'}:
					{String(request.title || request.id || 'Operator input required')}
				</p>
			{/each}
			{#if activeGate && !requests.some((request) => request.id === `gate:${activeGate}`)}
				<p>Approval gate: <code>{activeGate}</code></p>
			{/if}
			<p class="text-xs text-muted-foreground">
				Registration does not answer questions, resolve problems or grant approval. Review and act
				in the execution's decisions view.
			</p>
		</div>
	{:else}
		<p class="text-sm">No workflow input is currently waiting.</p>
	{/if}
	{#if approvals.length}
		<details class="text-xs">
			<summary class="cursor-pointer text-muted-foreground">Approval policy</summary>
			<ul class="mt-2 space-y-1">
				{#each approvals as [gate, value] (gate)}
					<li>
						<code>{gate}</code>:
						{record(value).policy === 'auto' ? 'Delegated by policy' : 'Explicit approval required'}
						{#if record(value).source}
							· {String(record(value).source)}{/if}
					</li>
				{/each}
			</ul>
		</details>
	{/if}
	<p class="text-xs text-muted-foreground">
		This preview describes the inspected PR revision. Hub checks the current evidence again when
		registering and advancing the execution.
	</p>
</section>
