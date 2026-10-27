<script lang="ts">
	import type { components } from '$lib/api';
	let { run }: { run: components['schemas']['PipelineRunRead'] } = $props();
	const record = (v: unknown): Record<string, unknown> =>
		v && typeof v === 'object' ? (v as Record<string, unknown>) : {};
	let progress = $derived(run.sdd_progress || {});
	let current = $derived(record(progress.current));
	let hold = $derived(record(progress.hold));
	let stage = $derived(record(current.stage));
	let requestCount = $derived(Array.isArray(current.requests) ? current.requests.length : 0);
	let message = $derived.by(() => {
		if (['completed', 'failed', 'canceled'].includes(run.state))
			return 'This execution has finished. Inspect its evidence and decision history below.';
		if (progress.error) return String(progress.error);
		if (hold.blocked)
			return 'Resolve the worker problem and record its resolution before resuming.';
		if (Array.isArray(current.pending_questions) && current.pending_questions.length)
			return 'Answer the open worker questions below before a gate can pass.';
		if (progress.lint_blocked)
			return 'Align and commit the devkit installation receipt, then enroll a new execution.';
		if (requestCount) return 'Review the evidence, then answer the workflow requests below.';
		if (progress.pr_draft && progress.approval)
			return 'Mark the pull request ready when it may be merged. Hub will check CI and merge policy.';
		if (run.state === 'awaiting_ci')
			return 'Waiting for CI and merge policy. Hub will recheck the inspected head and base.';
		if (current.next_skill)
			return `Agent next step: ${String(current.next_skill)}${stage.name ? ` · ${String(stage.name)}` : ''}.`;
		return (
			run.pause_reason || 'Hub will inspect the current workflow and dispatch the next activity.'
		);
	});
</script>

<section class="space-y-2 rounded-lg border bg-muted/20 p-4" aria-label="Next action">
	<h3 class="text-sm font-semibold">Next action</h3>
	<p class="text-sm leading-relaxed break-words">{message}</p>
	{#if run.sdd_snapshot?.handoff_from}<p class="text-xs break-all text-muted-foreground">
			Origin {String(run.sdd_snapshot.handoff_from)} → {String(run.sdd_snapshot.spec_dir)}
		</p>{/if}
</section>
