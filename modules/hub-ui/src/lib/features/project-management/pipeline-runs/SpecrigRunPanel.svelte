<script lang="ts">
	import { SvelteMap } from 'svelte/reactivity';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { Button } from '$lib/components/ui/button';
	let {
		run,
		onchange
	}: { run: components['schemas']['PipelineRunRead']; onchange: () => void | Promise<void> } =
		$props();
	let busy = $state(false);
	let error = $state('');
	let feedback = $state('');
	function record(value: unknown): Record<string, unknown> {
		return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
	}
	let progress = $derived(run.specrig_progress || {});
	let current = $derived(record(progress.current));
	let stage = $derived(record(current.stage));
	let approval = $derived(record(progress.approval));
	let spec = $derived(String(run.specrig_snapshot?.spec_dir || ''));
	let waiting = $derived(['paused', 'blocked'].includes(run.state));
	let terminal = $derived(['completed', 'failed', 'canceled'].includes(run.state));
	let canApprove = $derived(
		waiting && Array.isArray(stage.exit) && stage.exit.includes('approval-given')
	);
	let evidenceUrl = $derived(
		`${run.pull_url.split('/pull/')[0]}/tree/${progress.head_sha}/${spec}`
	);
	const ids = new SvelteMap<string, string>();
	async function decide(decision: 'approve' | 'revise' | 'reject' | 'revoke') {
		const intent = JSON.stringify([run.id, run.revision, decision, feedback]);
		if (!ids.has(intent)) ids.set(intent, crypto.randomUUID());
		busy = true;
		error = '';
		try {
			const result = await api.POST('/api/v1/pipeline-runs/{run_id}/resume', {
				params: { path: { run_id: run.id } },
				body: {
					request_id: ids.get(intent)!,
					expected_revision: run.revision,
					decision,
					feedback
				}
			});
			if (result.error) throw new Error(apiErrorMessage(result.error, 'Decision was not applied'));
			await onchange();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Decision failed';
		} finally {
			busy = false;
		}
	}
</script>

<section class="space-y-3 rounded border p-3">
	<h3 class="text-sm font-semibold">Specrig execution</h3>
	<p class="text-sm break-all">{spec}</p>
	<p class="text-sm">Stage: {String(stage.name || stage.id || 'Inspecting')}</p>
	<p class="text-xs break-all text-muted-foreground">
		Checked head {String(progress.head_sha || '')} · base {String(progress.base_sha || '')}
	</p>
	<a class="text-sm underline" href={evidenceUrl} target="_blank" rel="noreferrer"
		>Inspect spec, review, reconcile and final report at this commit</a
	>
	{#if Array.isArray(current.done)}<p class="text-xs">
			Verified stages: {current.done.join(', ')}
		</p>{/if}
	{#if approval.actor}<p class="text-sm">
			Integration authorization: {String(approval.actor)}
		</p>{/if}
	{#if !terminal}
		<label class="block text-sm"
			>Requested changes or decision reason
			<textarea
				class="mt-1 min-h-20 w-full rounded border bg-background p-2"
				maxlength="8000"
				bind:value={feedback}></textarea>
		</label>
		<div class="flex flex-wrap gap-2">
			{#if canApprove}<Button disabled={busy} onclick={() => void decide('approve')}
					>Approve integration</Button
				>{/if}
			{#if waiting}
				<Button
					variant="outline"
					disabled={busy || !feedback.trim()}
					onclick={() => void decide('revise')}>Request changes</Button
				>
				<Button variant="outline" disabled={busy} onclick={() => void decide('reject')}
					>Reject and stop</Button
				>
			{/if}
			{#if approval.actor}<Button
					variant="outline"
					disabled={busy}
					onclick={() => void decide('revoke')}>Revoke approval</Button
				>{/if}
		</div>
	{/if}
	{#if error}<p role="alert" class="text-sm text-destructive">{error}</p>{/if}
</section>
