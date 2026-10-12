<script lang="ts">
	import type { components } from '$lib/api';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { MessageSquare, Check } from '@lucide/svelte';
	let {
		question,
		actionable = false,
		disabled = false,
		onresume
	}: {
		question: components['schemas']['QuestionRead'];
		actionable?: boolean;
		disabled?: boolean;
		onresume: (id: string) => void;
	} = $props();
</script>

<article class="space-y-4 rounded-xl border bg-card p-4 sm:p-5">
	<div class="flex items-center justify-between gap-3 text-xs text-muted-foreground">
		<span class="flex items-center gap-2"
			><MessageSquare class="size-4" />{actionable ? 'Your input is needed' : 'Question'}</span
		>
		<Badge variant="outline" class="capitalize">{question.state}</Badge>
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
				{#if answer.applied_attempt_id}
					<span class="flex items-center gap-1 text-xs text-muted-foreground"
						><Check class="size-3" />Applied to an execution attempt</span
					>
				{:else if actionable}
					<Button size="sm" {disabled} onclick={() => onresume(answer.id)}
						>Resume with this answer</Button
					>
				{/if}
			</div>
		</div>
	{/each}
	{#if question.resolution}<p class="border-t pt-3 text-sm text-muted-foreground">
			{question.resolution}
		</p>{/if}
</article>
