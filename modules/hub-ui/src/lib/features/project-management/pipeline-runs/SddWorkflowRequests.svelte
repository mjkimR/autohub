<script lang="ts">
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { Button } from '$lib/components/ui/button';
	let {
		run,
		disabled = false,
		onchange,
		onbusychange = () => {}
	}: {
		run: components['schemas']['PipelineRunRead'];
		disabled?: boolean;
		onchange: () => void | Promise<void>;
		onbusychange?: (value: boolean) => void;
	} = $props();
	type Request = {
		id: string;
		kind: string;
		title: string;
		prompt: string;
		options: { id: string; description: string; eligible: boolean; recommended: boolean }[];
		// devkit: record (a decision record), given (--given) or envelope (a worker question, answered by an
		// answer envelope the agent writes). Questions are never declined or deferred.
		answer?: string;
		context?: string | null;
	};
	let engine = $derived((run.sdd_progress?.current || {}) as { requests?: Request[] });
	let requests = $derived(
		(engine.requests || []).filter((r: Request) => r.id !== 'gate:dev-integration') as Request[]
	);
	let selected = $state('');
	let note = $state('');
	let busy = $state(false);
	let error = $state('');
	let retry = $state<{ intent: string; id: string } | null>(null);
	let current = $derived(requests[0]);
	let question = $derived(current?.answer === 'envelope' || current?.id.startsWith('question:'));
	// Accepting or rejecting a proposal: Hub writes the decision commit itself on the head shown here.
	let planAccept = $derived(current?.id === 'gate:plan-accept');
	let headSha = $derived(
		String((run.sdd_progress as { head_sha?: unknown } | null)?.head_sha ?? '')
	);
	async function decidePlan(decision: 'accept_plan' | 'reject_plan') {
		if (!current || busy || disabled) return;
		const intent = JSON.stringify([run.id, run.revision, decision, headSha, note]);
		if (retry?.intent !== intent) retry = { intent, id: crypto.randomUUID() };
		busy = true;
		onbusychange(true);
		error = '';
		try {
			const result = await api.POST('/api/v1/pipeline-runs/{run_id}/resume', {
				params: { path: { run_id: run.id } },
				body: {
					request_id: retry!.id,
					expected_revision: run.revision,
					decision,
					head_sha: headSha,
					feedback: note
				}
			});
			if (result.error)
				throw new Error(apiErrorMessage(result.error, 'Could not record the decision'));
			await onchange();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not record the decision';
		} finally {
			busy = false;
			onbusychange(false);
		}
	}
	let answerable = $derived(
		!!current && (current.kind !== 'choose' || !!selected || (question && note.trim().length > 0))
	);
	$effect(() => {
		const key = `${run.id}:${run.revision}:${current?.id}`;
		if (key) {
			selected = '';
			note = '';
			error = '';
		}
	});
	async function answer(action: 'accept' | 'decline' | 'cancel') {
		if (!current || busy || disabled) return;
		const workflow_answer = {
			request: current.id,
			action,
			value: action === 'accept' && current.kind === 'choose' && selected ? selected : null
		};
		const intent = JSON.stringify([run.id, run.revision, workflow_answer, note]);
		if (retry?.intent !== intent) retry = { intent, id: crypto.randomUUID() };
		busy = true;
		onbusychange(true);
		error = '';
		try {
			const result = await api.POST('/api/v1/pipeline-runs/{run_id}/resume', {
				params: { path: { run_id: run.id } },
				body: {
					request_id: retry!.id,
					expected_revision: run.revision,
					workflow_answer,
					feedback: note
				}
			});
			if (result.error)
				throw new Error(apiErrorMessage(result.error, 'Could not record the decision'));
			await onchange();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not record the decision';
		} finally {
			busy = false;
			onbusychange(false);
		}
	}
</script>

{#if current && ['paused', 'blocked'].includes(run.state)}
	<section class="space-y-4 rounded-xl border bg-card p-4 sm:p-5" aria-label="SDD workflow request">
		<div>
			<p class="text-xs text-muted-foreground">
				{planAccept ? 'Proposal decision' : question ? 'Worker question' : 'Workflow decision'} · {current.id}
			</p>
			<h3 class="mt-1 font-semibold">{current.title}</h3>
			<p class="mt-2 text-sm">{current.prompt}</p>
			{#if current.context}<p class="mt-1 text-xs text-muted-foreground">
					Context: {current.context}
				</p>{/if}
		</div>
		{#if current.kind === 'choose'}
			<fieldset class="space-y-2" disabled={busy || disabled}>
				<legend class="mb-2 text-sm font-medium"
					>{question ? 'Choose an option' : 'Choose the next workflow'}</legend
				>
				{#each current.options as option (option.id)}
					<label
						class="flex gap-3 rounded-lg border p-3 text-sm"
						class:opacity-50={!option.eligible}
					>
						<input
							type="radio"
							name="sdd-workflow-choice"
							value={option.id}
							bind:group={selected}
							disabled={!option.eligible}
						/>
						<span
							><strong>{option.id}</strong>{option.recommended ? ' · Recommended' : ''}
							<span class="mt-1 block text-muted-foreground">{option.description}</span></span
						>
					</label>
				{/each}
			</fieldset>
		{/if}
		<label class="block space-y-2 text-sm"
			>{question
				? 'Decision (one sentence; required without an option)'
				: planAccept
					? 'Note (optional for acceptance; the rejection reason, kept in the commit message)'
					: 'Note (optional)'}
			<textarea
				class="min-h-20 w-full rounded-lg border bg-background p-3"
				maxlength="8000"
				bind:value={note}
				disabled={busy || disabled}></textarea>
		</label>
		{#if planAccept}
			<div class="flex flex-wrap gap-2">
				<Button
					disabled={busy || disabled || !headSha}
					onclick={() => void decidePlan('accept_plan')}
					>{busy ? 'Recording…' : 'Accept proposal'}</Button
				>
				<Button
					variant="destructive"
					disabled={busy || disabled || !headSha || !note.trim()}
					onclick={() => void decidePlan('reject_plan')}>Reject proposal</Button
				>
			</div>
			<p class="text-xs text-muted-foreground">
				Hub commits the decision on head <code>{headSha.slice(0, 12)}</code> without an agent:
				acceptance records <code>gate:plan-accept</code> and <code>status: accepted</code>,
				rejection only
				<code>status: rejected</code> with your reason. The pull request then merges by the project's
				policy.
			</p>
		{:else}
			<div class="flex flex-wrap gap-2">
				<Button disabled={busy || disabled || !answerable} onclick={() => void answer('accept')}
					>{busy
						? 'Recording…'
						: question
							? 'Record answer'
							: current.kind === 'choose'
								? 'Confirm choice'
								: 'Approve'}</Button
				>
				{#if !question}
					<Button
						variant="outline"
						disabled={busy || disabled}
						onclick={() => void answer('decline')}>Decline</Button
					>
					<Button variant="ghost" disabled={busy || disabled} onclick={() => void answer('cancel')}
						>Defer decision</Button
					>
				{/if}
			</div>
			<p class="text-xs text-muted-foreground">
				{#if question}
					The agent records this answer as an answer envelope on the pull request; the question
					stays open until that envelope exists.
				{:else}
					Declining or deferring leaves this request open. Neither action stops the run or withdraws
					integration approval.
				{/if}
			</p>
		{/if}
		{#if error}<p role="alert" class="text-sm text-destructive">{error}</p>{/if}
	</section>
{/if}
