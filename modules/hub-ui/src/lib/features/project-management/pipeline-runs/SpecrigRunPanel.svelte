<script lang="ts">
	import { SvelteMap } from 'svelte/reactivity';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import {
		ShieldCheck,
		FileText,
		GitCommitHorizontal,
		Check,
		ArrowRight,
		CirclePause
	} from '@lucide/svelte';
	import { tick } from 'svelte';
	import SpecrigReports from './SpecrigReports.svelte';
	let {
		run,
		onchange,
		disabled = false,
		questionPending = false,
		onbusychange = () => {}
	}: {
		run: components['schemas']['PipelineRunRead'];
		onchange: () => void | Promise<void>;
		disabled?: boolean;
		questionPending?: boolean;
		onbusychange?: (busy: boolean) => void;
	} = $props();
	let busy = $state(false);
	let error = $state('');
	let feedback = $state('');
	let mode = $state<'revise' | 'reject' | 'revoke' | null>(null);
	let editor = $state<HTMLTextAreaElement>();
	async function choose(action: typeof mode) {
		mode = action;
		error = '';
		await tick();
		editor?.focus();
	}
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
		progress.head_sha && spec
			? `${run.pull_url.split('/pull/')[0]}/tree/${progress.head_sha}/${spec}`
			: null
	);
	let workflow = $derived(record(progress.workflow));
	let stages = $derived(Array.isArray(workflow.stages) ? workflow.stages.map(record) : []);
	function stageName(id: unknown) {
		return String(stages.find((item) => item.id === id)?.name || id);
	}
	const ids = new SvelteMap<string, string>();
	async function decide(decision: 'approve' | 'revise' | 'reject' | 'revoke') {
		if (busy || disabled || questionPending) return;
		const intent = JSON.stringify([run.id, run.revision, decision, feedback]);
		if (!ids.has(intent)) ids.set(intent, crypto.randomUUID());
		busy = true;
		onbusychange(true);
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
			mode = null;
			feedback = '';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Decision failed';
		} finally {
			busy = false;
			onbusychange(false);
		}
	}
</script>

<section
	class="overflow-hidden rounded-xl border bg-card"
	aria-label="Specrig integration decision"
>
	<div class="space-y-4 p-4 sm:p-5">
		<div class="flex items-start gap-3">
			<div class="rounded-lg bg-primary/10 p-2 text-primary"><ShieldCheck class="size-5" /></div>
			<div class="min-w-0 flex-1">
				<p class="mb-1 text-xs font-medium tracking-wide text-muted-foreground uppercase">
					Specrig workflow
				</p>
				<h3 class="text-lg font-semibold">
					{terminal
						? 'Execution finished'
						: approval.actor
							? 'Integration authorized'
							: canApprove
								? 'Review & approve integration'
								: String(stage.name || stage.id || 'Inspecting workflow')}
				</h3>
			</div>
			<Badge variant="outline"
				>{terminal
					? 'Closed'
					: approval.actor
						? 'Approved'
						: canApprove
							? 'G3'
							: 'In progress'}</Badge
			>
		</div>
		{#if questionPending}<p
				class="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-sm"
			>
				Answer or dismiss the pending question above before making an integration decision.
			</p>
		{:else if progress.approval_withheld}<p class="text-sm leading-relaxed text-muted-foreground">
				Review the updated evidence and approve again in Hub. The existing PR ready status will not
				override your earlier feedback or revocation.
			</p>
		{:else if canApprove}<p class="text-sm leading-relaxed text-muted-foreground">
				Inspect the spec, reviews and final report before authorizing integration. {#if progress.waiting_for_approval}
					You can also mark the PR ready for review; Hub checks it automatically.{/if}
			</p>{/if}
		<div class="space-y-3 rounded-lg bg-muted/40 p-3">
			<div class="flex items-start gap-2">
				<FileText class="mt-0.5 size-4 shrink-0 text-muted-foreground" />
				<div class="min-w-0">
					<p class="mb-1 text-xs text-muted-foreground">Evidence at the inspected commit</p>
					{#if evidenceUrl}<a
							class="text-sm font-medium break-all underline underline-offset-4 hover:text-primary"
							href={evidenceUrl}
							target="_blank"
							rel="noreferrer">{spec}</a
						>{:else}<p class="text-sm text-muted-foreground">Evidence is not available yet.</p>{/if}
				</div>
			</div>
			<div class="flex flex-wrap gap-x-5 gap-y-2 border-t pt-3 text-xs">
				<span class="flex items-center gap-1.5"
					><GitCommitHorizontal class="size-3.5 text-muted-foreground" />Head
					<code title={String(progress.head_sha || '')}
						>{String(progress.head_sha || 'Pending').slice(0, 10)}</code
					></span
				><span class="text-muted-foreground"
					>Base <code title={String(progress.base_sha || '')}
						>{String(progress.base_sha || 'Pending').slice(0, 10)}</code
					></span
				>
			</div>
		</div>
		<SpecrigReports reports={progress.reports} {evidenceUrl} />
		{#if progress.lint_diagnostic}<p class="rounded-lg border border-amber-500/30 p-3 text-sm">
				{String(progress.lint_diagnostic)}
			</p>{/if}
		{#if Array.isArray(current.done) && current.done.length}
			<details class="text-xs">
				<summary class="cursor-pointer text-muted-foreground"
					>Verified stages · {current.done.length}</summary
				>
				<ul class="mt-3 grid gap-2 sm:grid-cols-2">
					{#each current.done as done (String(done))}<li class="flex items-start gap-2">
							<Check class="size-3.5 shrink-0 text-emerald-600 dark:text-emerald-400" />{stageName(
								done
							)}
						</li>{/each}
				</ul>
			</details>
		{/if}
		{#if approval.actor}<p class="text-xs text-muted-foreground">
				Authorized by <span class="font-medium text-foreground">{String(approval.actor)}</span>
			</p>{/if}
		{#if progress.pr_draft}<div
				class="flex items-start gap-2 rounded-lg border p-3 text-xs leading-relaxed text-muted-foreground"
			>
				<CirclePause class="mt-0.5 size-4 shrink-0" />
				<p>
					<strong class="font-medium text-foreground">PR is still a draft.</strong> Integration approval
					does not change draft status. Mark the PR ready when it may be merged.
				</p>
			</div>{/if}
	</div>
	{#if !terminal && (waiting || approval.actor)}
		<div class="space-y-4 border-t bg-muted/20 p-4 sm:px-5">
			{#if mode}
				<div class="space-y-3">
					<p class="text-sm font-semibold">
						{mode === 'revise'
							? 'What needs to change?'
							: mode === 'reject'
								? 'Stop this run'
								: 'Withdraw integration approval'}
					</p>
					{#if mode === 'reject'}<p class="text-xs leading-relaxed text-muted-foreground">
							The run will be canceled. Already dispatched agent work may continue.
						</p>{/if}
					<label class="block space-y-2 text-sm"
						>{mode === 'revise' ? 'Requested changes' : 'Decision reason (optional)'}<textarea
							bind:this={editor}
							class="min-h-24 w-full resize-y rounded-lg border bg-background px-3 py-2 text-sm leading-relaxed focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
							maxlength="8000"
							bind:value={feedback}
							disabled={busy || disabled || questionPending}
							placeholder={mode === 'revise'
								? 'Describe the changes and what should stay the same.'
								: 'Add context for the decision history.'}></textarea></label
					>
					<div class="flex flex-wrap items-center gap-2">
						<Button
							variant={mode === 'reject' ? 'destructive' : 'default'}
							disabled={busy ||
								disabled ||
								questionPending ||
								(mode === 'revise' && !feedback.trim())}
							onclick={() => mode && void decide(mode)}
							>{busy
								? 'Applying…'
								: mode === 'revise'
									? 'Send change request'
									: mode === 'reject'
										? 'Reject and stop'
										: 'Revoke approval'}</Button
						><Button
							variant="ghost"
							disabled={busy}
							onclick={() => {
								mode = null;
								feedback = '';
							}}>Cancel</Button
						>
					</div>
				</div>
			{:else}
				<div class="flex flex-wrap gap-2">
					{#if canApprove}<Button
							disabled={busy || disabled || questionPending}
							onclick={() => void decide('approve')}
							><ShieldCheck class="size-4" />{busy
								? 'Approving…'
								: 'Approve integration'}<ArrowRight class="size-4" /></Button
						>{/if}
					{#if waiting}<Button
							variant="outline"
							disabled={busy || disabled || questionPending}
							onclick={() => void choose('revise')}>Request changes</Button
						>{/if}
				</div>
				<details class="text-xs">
					<summary class="cursor-pointer text-muted-foreground">Other actions</summary>
					<div class="mt-3 flex flex-wrap gap-2">
						{#if waiting}<Button
								size="sm"
								variant="ghost"
								class="text-destructive"
								disabled={busy || disabled || questionPending}
								onclick={() => void choose('reject')}>Stop run</Button
							>{/if}{#if approval.actor}<Button
								size="sm"
								variant="outline"
								disabled={busy || disabled || questionPending}
								onclick={() => void choose('revoke')}>Withdraw approval</Button
							>{/if}
					</div>
				</details>
			{/if}
			{#if error}<p
					role="alert"
					class="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive"
				>
					{error}
				</p>{/if}
		</div>
	{/if}
</section>
