<script lang="ts">
	import { SvelteMap } from 'svelte/reactivity';
	import DecisionOutcome from './DecisionOutcome.svelte';
	import { decisionIntent, decisionBasis } from './decision-intents.svelte';
	import SddRunPanel from './SddRunPanel.svelte';
	import SddDecisionHistory from './SddDecisionHistory.svelte';
	import DecisionQuestion from './DecisionQuestion.svelte';
	import { RefreshCw, CircleHelp, CircleCheck, History } from '@lucide/svelte';
	import { onMount, untrack } from 'svelte';
	import { api, type components } from '$lib/api';
	import { responseData } from '$lib/api/pagination';
	import { Button } from '$lib/components/ui/button';
	import { Textarea } from '$lib/components/ui/textarea';
	import { Input } from '$lib/components/ui/input';
	type Run = components['schemas']['PipelineRunRead'];
	type Question = components['schemas']['QuestionRead'];
	let {
		run,
		onchange,
		onrun,
		onRunPage = false,
		selection
	}: {
		run: Run;
		onchange: () => void;
		/** Receives each consistent run read, so a parent header can show the current state. */
		onrun?: (run: Run) => void;
		/** On the PR run page the header shows the wait reason and the next-step section the ended-run guidance. */
		onRunPage?: boolean;
		selection?: components['schemas']['DecisionEntryRead'];
	} = $props();
	let current = $state(untrack(() => run));
	let questions = $state<Question[]>([]);
	let total = $state(0);
	let offset = $state(0);
	let revision = $state(untrack(() => run.revision));
	let text = $state('');
	let reason = $state('');
	let error = $state('');
	let busy = $state(false);
	let decisionBusy = $state(false);
	let recoveryOpen = $state(false);
	let recoveryBasis = $state('');
	let recovery = $derived(decisionIntent(run.id, true));
	async function reviewRecovery() {
		await load(false);
		recoveryBasis = head;
		recoveryOpen = true;
	}
	async function reconcilePublication() {
		await recovery.submit(
			'resume',
			{ request_id: crypto.randomUUID(), expected_revision: revision },
			recoveryBasis
		);
		await afterMutation();
	}
	let review = $derived(decisionIntent(run.id));
	let head = $derived(decisionBasis(current));
	let locked = $derived(busy || decisionBusy || review.unresolved || recovery.unresolved);
	let ready = $state(false);
	let loadedAt = $state('');
	let saved = $state('');
	let pending = $derived(
		questions.find(
			(q) =>
				(!selection || q.id === selection.subject_id) &&
				(q.state === 'open' || q.state === 'answered')
		)
	);
	let terminal = $derived(['completed', 'failed', 'canceled'].includes(current.state));
	let pastQuestions = $derived(questions.filter((q) => q.id !== pending?.id));
	const requests = new SvelteMap<string, string>();
	function requestId(key: string) {
		if (!requests.has(key)) requests.set(key, crypto.randomUUID());
		return requests.get(key)!;
	}
	async function load(inspectSelection = true) {
		ready = false;
		if (selection && inspectSelection) {
			responseData(
				await api.POST('/api/v1/pipeline-runs/decisions/review', {
					body: { key: selection.key, fingerprint: selection.fingerprint }
				}),
				'Subject changed or inspection failed. Close, refresh and Review again.'
			);
		}
		const [q, r] = await Promise.all([
			api.GET('/api/v1/pipeline-runs/{run_id}/questions', {
				params: { path: { run_id: run.id }, query: { offset, limit: 20 } }
			}),
			api.GET('/api/v1/pipeline-runs/{run_id}', { params: { path: { run_id: run.id } } })
		]);
		const data = responseData(q, 'Unable to load decisions');
		const latest = responseData(r, 'Unable to load run');
		if (latest.revision !== data.run_revision) {
			throw new Error('Run changed while loading decisions. Refresh before making a decision.');
		}
		questions = data.items;
		if (selection && ['run-question', 'native-hub-question'].includes(selection.kind)) {
			const selected = responseData(
				await api.GET('/api/v1/pipeline-runs/{run_id}/questions/{question_id}', {
					params: { path: { run_id: run.id, question_id: selection.subject_id } }
				}),
				'Selected question is unavailable'
			);
			if (!questions.some((q) => q.id === selected.id)) questions = [selected, ...questions];
		}
		total = data.total_count;
		revision = data.run_revision;
		current = latest;
		onrun?.(latest);
		loadedAt = new Date().toLocaleString();
		ready = !selection || inspectSelection || (selection.kind === 'run-question' && !!pending);
	}
	async function afterMutation() {
		onchange();
		if (!selection) {
			try {
				await load();
			} catch {
				ready = false;
				error = 'Recorded. Refresh failed; retry read.';
			}
			return;
		}
		try {
			await load(false);
		} catch {
			ready = false;
			saved ||= 'Decision recorded. Refresh failed. Retry read to review its current subject.';
		}
	}
	async function perform(action: () => Promise<void>) {
		busy = true;
		error = '';
		saved = '';
		try {
			await action();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Operation failed';
		} finally {
			busy = false;
		}
	}
	async function submit() {
		if (decisionBusy || !ready || offset !== 0) return;
		// An uncertain answer keeps its identity across refreshes, even when its save
		// already advanced the revision. Acknowledgement ends this submission intent.
		const key = pending
			? JSON.stringify(['answer', pending.id, text])
			: JSON.stringify(['ask', revision, text]);
		const request = {
			request_id: requestId(key),
			expected_revision: revision
		};
		await review.submit(
			pending ? 'answer' : 'question',
			pending ? { ...request, answer: text } : { ...request, question: text },
			head,
			pending?.id
		);
		saved = pending
			? 'Answer saved. The run remains stopped until you resume.'
			: 'Question recorded. Hub progression is blocked.';
		requests.delete(key);
		text = '';
		await afterMutation();
	}
	async function resume(answerId?: string) {
		if (decisionBusy || !ready || offset !== 0) return;
		await review.submit(
			'resume',
			{
				request_id: crypto.randomUUID(),
				expected_revision: revision,
				answer_id: answerId
			},
			head
		);
		await afterMutation();
		saved = 'Resume recorded. Agent delivery may still be pending.';
	}
	// Save and resume (DecisionQuestion): two owner requests; failures throw so the composer can
	// show an unsaved or saved-but-not-resumed state instead of a section-level error.
	async function saveAnswer(answer: string) {
		if (decisionBusy || !ready || offset !== 0 || !pending)
			throw new Error('Decisions are not current. Refresh decisions first.');
		// An identity confirmed through Retry same request is finished; a new save is a new request.
		for (const [key, id] of requests)
			if (review.intent?.acknowledged && review.intent.requestId === id) requests.delete(key);
		text = answer;
		busy = true;
		error = '';
		saved = '';
		try {
			await submit();
		} finally {
			busy = false;
		}
		return review.outcome?.answer_id ?? undefined;
	}
	async function resumeAnswer(answerId: string) {
		if (decisionBusy || !ready || offset !== 0)
			throw new Error('Decisions are not current. Refresh decisions before resuming.');
		busy = true;
		error = '';
		try {
			await resume(answerId);
		} finally {
			busy = false;
		}
	}
	async function dismiss() {
		if (decisionBusy || !ready || offset !== 0 || !pending) return;
		responseData(
			await api.POST('/api/v1/pipeline-runs/{run_id}/questions/{question_id}/dismiss', {
				params: { path: { run_id: run.id, question_id: pending.id } },
				body: { expected_revision: revision, reason }
			}),
			'Unable to dismiss question'
		);
		reason = '';
		await afterMutation();
	}
	onMount(() => {
		void perform(() => load());
	});
</script>

<div class="mb-5 flex flex-wrap items-center gap-x-3 gap-y-2">
	<Button
		variant="ghost"
		size="sm"
		disabled={busy || decisionBusy}
		onclick={() => perform(() => load())}
		><RefreshCw class={busy ? 'size-3.5 animate-spin' : 'size-3.5'} />Refresh decisions</Button
	>
	{#if loadedAt}<p class="text-xs text-muted-foreground">Last loaded: {loadedAt}</p>{/if}
</div>
{#if error}<div
		role="alert"
		class="mb-5 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive"
	>
		{error}
	</div>{/if}
{#if saved}<div
		role="status"
		class="mb-5 flex items-start gap-2 rounded-lg border bg-muted/50 p-3 text-sm"
	>
		<CircleCheck class="mt-0.5 size-4 shrink-0" />{saved}
	</div>{/if}
{#if !ready && !error}<p role="status" class="mb-5 text-sm text-muted-foreground">
		Loading the latest decisions…
	</p>{/if}
<div class="flex flex-col gap-6 md:flex-row md:items-start">
	<div class="min-w-0 flex-1 space-y-5">
		{#if ready && !pending && !current.sdd_snapshot && total === 0}<p
				class="text-sm text-muted-foreground"
			>
				{terminal ? 'No questions or SDD activity.' : 'No questions or SDD activity yet.'}
			</p>{/if}
		{#if !onRunPage && current.pause_reason}
			<div class="rounded-xl border bg-muted/40 p-4">
				<p
					class="mb-2 flex items-center gap-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase"
				>
					<CircleHelp class="size-4" />Current wait
				</p>
				<p class="text-sm leading-relaxed break-words whitespace-pre-wrap">
					{current.pause_reason}
				</p>
			</div>
		{/if}
		{#if terminal && !onRunPage}<div
				class="rounded-xl border bg-muted/40 p-4 text-sm leading-relaxed"
			>
				This run has ended. For failed or canceled work, inspect the PR and register replacement
				work. The original result is preserved.
			</div>{/if}
		{#if pending}
			<DecisionQuestion
				question={pending}
				actionable={!terminal && offset === 0}
				disabled={locked || !ready}
				onoutcome={(id) => void perform(() => review.check('answer', id))}
				onresume={resumeAnswer}
				onsave={saveAnswer}
			/>
		{/if}
		{#if ready && !terminal && offset === 0 && pending}
			<section class="space-y-3" aria-label="Dismiss the pending question">
				<details class="rounded-lg border p-3 text-sm">
					<summary class="cursor-pointer font-medium">Dismiss this question</summary>
					<div class="mt-3 space-y-3">
						<label class="block space-y-2"
							>Reason to dismiss<Input
								maxlength={2000}
								bind:value={reason}
								disabled={locked}
							/></label
						><Button
							variant="outline"
							disabled={locked || !reason.trim()}
							onclick={() => perform(dismiss)}>Dismiss without resuming</Button
						>
					</div>
				</details>
			</section>
		{/if}
		{#if current.sdd_snapshot}
			<SddRunPanel
				showOutcome={false}
				onreconcile={async () => {
					await perform(reviewRecovery);
				}}
				run={current}
				disabled={locked || !ready || offset !== 0}
				questionPending={!!pending}
				selectedRequestId={selection &&
				!['run-question', 'native-hub-question'].includes(selection.kind)
					? selection.subject_id
					: undefined}
				onbusychange={(value) => {
					decisionBusy = value;
				}}
				onchange={async () => {
					await afterMutation();
				}}
			/>
		{/if}
		<DecisionOutcome
			runId={run.id}
			{head}
			{revision}
			{terminal}
			onrefresh={() => load(false)}
			onreconcile={reviewRecovery}
		/>
		{#if recoveryOpen}<section
				class="space-y-2 rounded-lg border p-3"
				aria-label="Publication reconciliation"
			>
				<p>
					Current evidence reviewed. Confirm inspection and possible continuation using a separate
					recovery request.
				</p>
				<Button
					disabled={busy ||
						terminal ||
						head !== recoveryBasis ||
						recovery.unresolved ||
						!['paused', 'blocked'].includes(current.state)}
					onclick={() => perform(reconcilePublication)}>Confirm publication reconciliation</Button
				>
				<DecisionOutcome
					recovery={true}
					runId={run.id}
					{head}
					{revision}
					{terminal}
					onrefresh={() => load(false)}
				/>
			</section>{/if}
		{#if ready && !terminal && offset === 0 && !pending}
			{#if current.state === 'paused' || current.state === 'blocked'}
				<details open={!current.sdd_snapshot} class="rounded-xl border p-4 text-sm">
					<summary class="cursor-pointer font-medium">Recovery & inspection</summary>
					<p class="my-3 text-muted-foreground">
						Recheck this run after resolving its wait. This action does not grant integration
						approval.
					</p>
					<Button variant="outline" disabled={locked} onclick={() => perform(() => resume())}
						>Resume after inspection</Button
					>
				</details>
			{/if}
			<details class="rounded-xl border p-4 text-sm">
				<summary class="cursor-pointer font-medium">Ask a new question</summary>
				<div class="mt-4 space-y-3">
					<label class="block space-y-2"
						>Question requiring a decision<Textarea
							class="min-h-24"
							maxlength={8000}
							bind:value={text}
							disabled={locked}
						/></label
					><Button
						variant="outline"
						disabled={locked || !text.trim()}
						onclick={() => perform(submit)}>Ask and pause</Button
					>
				</div>
			</details>
		{/if}
	</div>
	<aside
		class="min-w-0 space-y-5 md:w-70 md:shrink-0 md:border-l md:pl-5"
		aria-label="Decision history"
	>
		{#if current.sdd_snapshot}<SddDecisionHistory
				runId={run.id}
				{revision}
				disabled={locked || !ready || offset !== 0}
				onchange={async () => {
					await afterMutation();
				}}
			/>{/if}
		<section class="space-y-3">
			<h3 class="flex items-center gap-2 text-sm font-semibold">
				<History class="size-4 text-muted-foreground" />Question history
			</h3>
			{#if ready && pastQuestions.length === 0}<p
					class="text-xs leading-relaxed text-muted-foreground"
				>
					No earlier questions on this page.
				</p>{/if}
			{#each pastQuestions as question (question.id)}<details class="rounded-lg border p-3">
					<summary class="cursor-pointer text-sm leading-relaxed break-words"
						>{question.question}</summary
					>
					<div class="mt-3">
						<DecisionQuestion
							{question}
							onresume={() => {}}
							onoutcome={(id) => void perform(() => review.check('answer', id))}
						/>
					</div>
				</details>{/each}
			{#if total > 20}<div class="flex items-center justify-between gap-2">
					<Button
						size="sm"
						variant="outline"
						disabled={locked || offset === 0}
						onclick={() => {
							offset -= 20;
							void perform(load);
						}}>Previous</Button
					><span class="text-xs text-muted-foreground"
						>{Math.floor(offset / 20) + 1} / {Math.ceil(total / 20)}</span
					><Button
						size="sm"
						variant="outline"
						disabled={locked || offset + 20 >= total}
						onclick={() => {
							offset += 20;
							void perform(load);
						}}>Next</Button
					>
				</div>{/if}
		</section>
		<p class="border-t pt-4 text-xs leading-relaxed text-muted-foreground">
			Pausing Hub does not stop an agent already running. Check its progress before resuming.
		</p>
	</aside>
</div>
