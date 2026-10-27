<script lang="ts">
	import { SvelteMap } from 'svelte/reactivity';
	import SddRunPanel from './SddRunPanel.svelte';
	import SddDecisionHistory from './SddDecisionHistory.svelte';
	import DecisionQuestion from './DecisionQuestion.svelte';
	import { Badge } from '$lib/components/ui/badge';
	import { getStateBadgeClass } from './presentation';
	import { RefreshCw, ExternalLink, CircleHelp, CircleCheck, History } from '@lucide/svelte';
	import { onMount, untrack } from 'svelte';
	import { api, type components } from '$lib/api';
	import { responseData } from '$lib/api/pagination';
	import { Button } from '$lib/components/ui/button';
	import {
		Dialog,
		DialogContent,
		DialogHeader,
		DialogTitle,
		DialogDescription
	} from '$lib/components/ui/dialog';
	type Run = components['schemas']['PipelineRunRead'];
	type Question = components['schemas']['QuestionRead'];
	let { run, onclose, onchange }: { run: Run; onclose: () => void; onchange: () => void } =
		$props();
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
	let locked = $derived(busy || decisionBusy);
	let ready = $state(false);
	let saved = $state('');
	let pending = $derived(questions.find((q) => q.state === 'open' || q.state === 'answered'));
	let terminal = $derived(['completed', 'failed', 'canceled'].includes(current.state));
	let pastQuestions = $derived(questions.filter((q) => q.id !== pending?.id));
	const requests = new SvelteMap<string, string>();
	function requestId(key: string) {
		if (!requests.has(key)) requests.set(key, crypto.randomUUID());
		return requests.get(key)!;
	}
	async function load() {
		ready = false;
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
		total = data.total_count;
		revision = data.run_revision;
		current = latest;
		ready = true;
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
		if (pending) {
			responseData(
				await api.POST('/api/v1/pipeline-runs/{run_id}/questions/{question_id}/answers', {
					params: { path: { run_id: run.id, question_id: pending.id } },
					body: { ...request, answer: text }
				}),
				'Unable to save answer'
			);
			saved = 'Answer saved. The run remains stopped until you resume.';
		} else {
			responseData(
				await api.POST('/api/v1/pipeline-runs/{run_id}/questions', {
					params: { path: { run_id: run.id } },
					body: { ...request, question: text }
				}),
				'Unable to record question'
			);
			saved = 'Question recorded. Hub progression is blocked.';
		}
		requests.delete(key);
		text = '';
		await load();
		onchange();
	}
	async function resume(answerId?: string) {
		if (decisionBusy || !ready || offset !== 0) return;
		responseData(
			await api.POST('/api/v1/pipeline-runs/{run_id}/resume', {
				params: { path: { run_id: run.id } },
				body: {
					request_id: requestId(`resume:${revision}:${answerId ?? ''}`),
					expected_revision: revision,
					answer_id: answerId
				}
			}),
			'Unable to resume; refresh and inspect the current run before changing your request'
		);
		await load();
		onchange();
		saved = 'Resume recorded. Agent delivery may still be pending.';
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
		await load();
		onchange();
	}
	onMount(() => {
		void perform(load);
	});
</script>

<Dialog
	open={true}
	onOpenChange={(open) => {
		if (!open) onclose();
	}}
>
	<DialogContent
		class="flex max-h-[calc(100dvh-2rem)] flex-col gap-0 overflow-hidden p-0 sm:max-w-[1040px]"
	>
		<DialogHeader class="shrink-0 border-b px-5 py-5 sm:px-7">
			<div class="mb-2 flex items-center gap-2 pr-8">
				<Badge variant="outline">PR #{run.pull_number}</Badge>
				<Badge variant="outline" class={getStateBadgeClass(current.state)}
					>{current.state.replaceAll('_', ' ')}</Badge
				>
				{#if current.sdd_snapshot}<span class="text-xs text-muted-foreground">sdd</span>{/if}
			</div>
			<DialogTitle class="text-xl leading-snug break-words"
				>{current.pull_snapshot.title}</DialogTitle
			>
			<DialogDescription
				>Review the evidence and choose the next step for this run.</DialogDescription
			>
			<div class="mt-3 flex flex-wrap items-center gap-2">
				<Button variant="outline" size="sm" href={run.pull_url} target="_blank" rel="noreferrer"
					><ExternalLink class="size-3.5" />Inspect pull request</Button
				>
				<Button variant="ghost" size="sm" disabled={locked} onclick={() => perform(load)}
					><RefreshCw class={busy ? 'size-3.5 animate-spin' : 'size-3.5'} />Refresh decisions</Button
				>
			</div>
		</DialogHeader>
		<div class="min-h-0 overflow-y-auto px-5 py-5 sm:px-7">
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
			{#if !ready && !error}<p
					role="status"
					class="mb-5 animate-pulse text-sm text-muted-foreground"
				>
					Loading the latest decisions…
				</p>{/if}
			<div class="grid items-start gap-6 md:grid-cols-[minmax(0,1fr)_280px]">
				<div class="min-w-0 space-y-5">
					{#if current.pause_reason}
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
					{#if terminal}<div class="rounded-xl border bg-muted/40 p-4 text-sm leading-relaxed">
							This run has ended. For failed or canceled work, inspect the PR and register
							replacement work. The original result is preserved.
						</div>{/if}
					{#if pending}
						<DecisionQuestion
							question={pending}
							actionable={!terminal && offset === 0}
							disabled={locked || !ready}
							onresume={(id) => void perform(() => resume(id))}
						/>
					{/if}
					{#if ready && !terminal && offset === 0 && pending}
						<section class="space-y-3" aria-label="Answer the pending question">
							<label class="block space-y-2 text-sm font-medium"
								>Your answer<textarea
									class="min-h-28 w-full resize-y rounded-lg border bg-background px-3 py-2 text-sm leading-relaxed font-normal focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
									maxlength="8000"
									placeholder="Describe the decision and any constraints to keep."
									disabled={locked}
									bind:value={text}></textarea></label
							>
							<div class="flex flex-wrap items-center justify-between gap-3">
								<p class="text-xs text-muted-foreground">
									Saving keeps the run paused. Resume with a saved answer when ready.
								</p>
								<Button disabled={locked || !text.trim()} onclick={() => perform(submit)}
									>Save answer</Button
								>
							</div>
							<details class="rounded-lg border p-3 text-sm">
								<summary class="cursor-pointer font-medium">Dismiss this question</summary>
								<div class="mt-3 space-y-3">
									<label class="block space-y-2"
										>Reason to dismiss<input
											class="w-full rounded-md border bg-background p-2"
											maxlength="2000"
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
							run={current}
							disabled={locked || !ready || offset !== 0}
							questionPending={!!pending}
							onbusychange={(value) => {
								decisionBusy = value;
							}}
							onchange={async () => {
								await load();
								onchange();
							}}
						/>
					{/if}
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
									>Question requiring a decision<textarea
										class="min-h-24 w-full rounded-lg border bg-background p-3"
										maxlength="8000"
										bind:value={text}
										disabled={locked}></textarea></label
								><Button
									variant="outline"
									disabled={locked || !text.trim()}
									onclick={() => perform(submit)}>Ask and pause</Button
								>
							</div>
						</details>
					{/if}
				</div>
				<aside class="min-w-0 space-y-5 md:border-l md:pl-5" aria-label="Decision history">
					{#if current.sdd_snapshot}<SddDecisionHistory
							runId={run.id}
							{revision}
							disabled={locked || !ready || offset !== 0}
							onchange={async () => {
								await load();
								onchange();
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
								<div class="mt-3"><DecisionQuestion {question} onresume={() => {}} /></div>
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
		</div>
	</DialogContent>
</Dialog>
