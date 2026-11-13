<script lang="ts">
	import type { components } from '$lib/api';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { MessageSquare, Check } from '@lucide/svelte';
	import { questionStateLabel } from './presentation';
	import DecisionAnswerComposer from './DecisionAnswerComposer.svelte';
	let {
		question,
		actionable = false,
		disabled = false,
		onresume,
		onoutcome = () => {},
		onsave
	}: {
		question: components['schemas']['QuestionRead'];
		actionable?: boolean;
		disabled?: boolean;
		/** Resume with the selected saved answer; a rejected promise marks Save and resume partial. */
		onresume: (id: string) => void | Promise<unknown>;
		onoutcome?: (id: string) => void;
		/** Save an answer and resolve with its saved answer ID; enables the answer composer. */
		onsave?: (answer: string) => Promise<string | undefined | void>;
	} = $props();
	let resumeError = $state<{ id: string; message: string } | null>(null);
	async function resumeWith(id: string) {
		resumeError = null;
		try {
			await onresume(id);
		} catch (e) {
			resumeError = { id, message: e instanceof Error ? e.message : 'Resume failed' };
		}
	}
</script>

<article class="space-y-4 rounded-xl border bg-card p-4 sm:p-5">
	<div class="flex items-center justify-between gap-3 text-xs text-muted-foreground">
		<span class="flex items-center gap-2"
			><MessageSquare class="size-4" />{actionable ? 'Your input is needed' : 'Question'}</span
		>
		<Badge variant="outline">{questionStateLabel(question.state)}</Badge>
	</div>
	<p class="text-base leading-relaxed font-medium break-words whitespace-pre-wrap">
		{question.question}
	</p>
	<p class="text-xs text-muted-foreground">
		{question.actor} · {new Date(question.created_at).toLocaleString()}
	</p>
	{#each question.answers as answer (answer.id)}
		<div class="space-y-3 rounded-lg bg-muted/50 p-3">
			<p class="text-sm leading-relaxed break-words whitespace-pre-wrap">{answer.answer}</p>
			<div class="flex flex-wrap items-center justify-between gap-3">
				<p class="text-xs text-muted-foreground">
					{answer.actor} · {new Date(answer.created_at).toLocaleString()}
				</p>
				<Button size="sm" variant="ghost" onclick={() => onoutcome(answer.id)}
					>Check saved answer outcome</Button
				>
				{#if answer.applied_attempt_id}
					<span class="flex items-center gap-1 text-xs text-muted-foreground"
						><Check class="size-3" />Applied to an execution attempt</span
					>
				{:else if actionable}
					<Button size="sm" {disabled} onclick={() => resumeWith(answer.id)}
						>Resume with this answer</Button
					>
				{/if}
			</div>
			{#if resumeError?.id === answer.id}<p role="alert" class="text-sm text-destructive">
					{resumeError.message}
				</p>{/if}
		</div>
	{/each}
	{#if actionable && onsave}
		<!-- A saved, unapplied answer owes an explicit resume; writing a different answer is secondary. -->
		<DecisionAnswerComposer
			{disabled}
			{onsave}
			{onresume}
			secondary={(question.answers ?? []).some((answer) => !answer.applied_attempt_id)}
		/>
	{/if}
	{#if question.resolution}<p class="border-t pt-3 text-sm text-muted-foreground">
			{question.resolution}
		</p>{/if}
</article>
