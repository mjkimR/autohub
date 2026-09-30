<script lang="ts">
	import { SvelteMap } from 'svelte/reactivity';
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
	let ready = $state(false);
	let saved = $state('');
	let pending = $derived(questions.find((q) => q.state === 'open' || q.state === 'answered'));
	let terminal = $derived(['completed', 'failed', 'canceled'].includes(current.state));
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
		if (!ready || offset !== 0) return;
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
		if (!ready || offset !== 0) return;
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
		if (!ready || offset !== 0 || !pending) return;
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
	<DialogContent class="max-h-[calc(100dvh-2rem)] overflow-y-auto sm:max-w-[680px]">
		<DialogHeader>
			<DialogTitle>Decisions for PR #{run.pull_number}</DialogTitle>
			<DialogDescription
				>Read the question, save your response, then choose whether to resume.</DialogDescription
			>
		</DialogHeader>
		<p class="text-sm">{current.pull_snapshot.title} · {current.state}</p>
		<a class="text-sm underline" href={run.pull_url} target="_blank" rel="noreferrer"
			>Inspect pull request</a
		>
		{#if current.pause_reason}<p class="text-sm whitespace-pre-wrap">{current.pause_reason}</p>{/if}
		<p class="text-sm text-muted-foreground">
			Pausing Hub does not stop an agent already running. Check its progress before resuming.
		</p>
		{#if terminal}
			<p class="rounded border p-3 text-sm">
				This run has ended. For failed or canceled work, register a replacement plan after checking
				the PR. Keep the original result and rebuild any unstarted dependents explicitly; a
				replacement does not release them automatically.
			</p>
		{/if}
		{#if error}<p role="alert" class="text-sm text-destructive">{error}</p>{/if}
		{#if saved}<p role="status" class="text-sm">{saved}</p>{/if}
		<Button variant="outline" disabled={busy} onclick={() => perform(load)}
			>Refresh decisions</Button
		>
		{#each questions as question (question.id)}
			<section class="space-y-3 rounded border p-3">
				<p class="font-medium whitespace-pre-wrap">{question.question}</p>
				<p class="text-xs text-muted-foreground">
					{question.state} · {new Date(question.created_at).toLocaleString()} · {question.actor}
				</p>
				{#each question.answers as answer (answer.id)}
					<div class="space-y-2 border-l-2 pl-3">
						<p class="text-sm whitespace-pre-wrap">{answer.answer}</p>
						<p class="text-xs text-muted-foreground">
							{answer.actor} · {new Date(answer.created_at).toLocaleString()}
						</p>
						{#if answer.applied_attempt_id}<p class="text-xs">Applied to an execution attempt</p>
						{:else if !terminal && pending?.id === question.id}
							<Button
								disabled={busy || !ready || offset !== 0}
								onclick={() => perform(() => resume(answer.id))}>Resume with this answer</Button
							>
						{/if}
					</div>
				{/each}
				{#if question.resolution}<p class="text-sm">{question.resolution}</p>{/if}
			</section>
		{/each}
		{#if ready && !terminal && offset === 0}
			<label class="space-y-2 text-sm"
				>{pending ? 'Your answer' : 'Question requiring a decision'}
				<textarea
					class="min-h-24 w-full rounded border bg-background p-2"
					maxlength="8000"
					bind:value={text}></textarea>
			</label>
			<Button disabled={busy || !text.trim()} onclick={() => perform(submit)}
				>{pending ? 'Save answer' : 'Ask and pause'}</Button
			>
			{#if pending}
				<label class="space-y-2 text-sm"
					>Reason to dismiss
					<input
						class="w-full rounded border bg-background p-2"
						maxlength="2000"
						bind:value={reason}
					/>
				</label>
				<Button variant="outline" disabled={busy || !reason.trim()} onclick={() => perform(dismiss)}
					>Dismiss without resuming</Button
				>
			{:else if current.state === 'paused' || current.state === 'blocked'}
				<Button disabled={busy} onclick={() => perform(() => resume())}
					>Resume after inspection</Button
				>
			{/if}
		{/if}
		{#if total > 20}
			<div class="flex gap-2">
				<Button
					variant="outline"
					disabled={busy || offset === 0}
					onclick={() => {
						offset -= 20;
						void perform(load);
					}}>Previous</Button
				>
				<Button
					variant="outline"
					disabled={busy || offset + 20 >= total}
					onclick={() => {
						offset += 20;
						void perform(load);
					}}>Next</Button
				>
			</div>
		{/if}
	</DialogContent>
</Dialog>
