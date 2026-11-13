<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Textarea } from '$lib/components/ui/textarea';
	// Save and resume stays two owner requests: the answer is saved first, then the run resumes
	// with that exact saved answer selected (DEC-01, DEC-07). A failed resume never discards the save.
	let {
		disabled = false,
		secondary = false,
		onsave,
		onresume
	}: {
		disabled?: boolean;
		/** Render both actions as secondary when another action (a saved answer's resume) is owed. */
		secondary?: boolean;
		onsave: (answer: string) => Promise<string | undefined | void>;
		onresume: (answerId: string) => void | Promise<unknown>;
	} = $props();
	let text = $state('');
	let working = $state<'save' | 'resume' | null>(null);
	let error = $state('');
	let partial = $state<string | null>(null);
	let locked = $derived(disabled || !!working);
	let expanded = $state(false);
	// Unsent text is never hidden when the composer turns secondary.
	$effect(() => {
		if (secondary && text.trim()) expanded = true;
	});
	function message(e: unknown, fallback: string) {
		return e instanceof Error && e.message ? e.message : fallback;
	}
	async function save(resume: boolean) {
		if (locked || !text.trim()) return;
		working = 'save';
		error = '';
		partial = null;
		let answerId: string | undefined;
		try {
			answerId = (await onsave(text)) || undefined;
		} catch (e) {
			// Unsaved or uncertain: keep the text and never resume on an unconfirmed save.
			error = `Answer not saved. ${message(e, 'Check the outcome before trying again.')}`;
			working = null;
			return;
		}
		text = '';
		working = null;
		if (!resume) return;
		if (!answerId) {
			partial = 'The saved answer could not be identified, so no resume was sent.';
			return;
		}
		// The resume is its own request: an unknown or refused outcome is recovered through the
		// decision outcome and the saved answer's own Resume action, never by re-saving.
		working = 'resume';
		try {
			await onresume(answerId);
		} catch (e) {
			partial = message(e, 'Resume failed.');
		} finally {
			working = null;
		}
	}
</script>

{#snippet form()}
	<label class="block space-y-2 text-sm font-medium"
		>Your answer<Textarea
			class="min-h-28 leading-relaxed font-normal"
			maxlength={8000}
			placeholder="Describe the decision and any constraints to keep."
			disabled={locked}
			bind:value={text}
		/></label
	>
	<div class="flex flex-wrap items-center justify-between gap-3">
		<p class="text-xs text-muted-foreground">
			Save and resume applies this answer and continues the run. Save only keeps the run paused.
		</p>
		<div class="flex flex-wrap gap-2">
			<Button variant="outline" disabled={locked || !text.trim()} onclick={() => save(false)}
				>Save only</Button
			>
			<Button
				variant={secondary ? 'outline' : 'default'}
				disabled={locked || !text.trim()}
				onclick={() => save(true)}
				>{working === 'save'
					? 'Saving…'
					: working === 'resume'
						? 'Resuming…'
						: 'Save and resume'}</Button
			>
		</div>
	</div>
{/snippet}

<section class="space-y-3" aria-label="Answer the pending question">
	{#if secondary}
		<details class="rounded-lg border p-3 text-sm" bind:open={expanded}>
			<summary class="cursor-pointer font-medium">Answer differently</summary>
			<div class="mt-3 space-y-3">{@render form()}</div>
		</details>
	{:else}
		{@render form()}
	{/if}
	{#if error}<p
			role="alert"
			class="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive"
		>
			{error}
		</p>{/if}
	{#if partial}
		<div
			role="alert"
			class="space-y-2 rounded-lg border border-warning/30 bg-warning/5 p-3 text-sm"
		>
			<p class="font-medium">Answer saved, but the run did not resume.</p>
			<p>{partial}</p>
			<p class="text-muted-foreground">
				The run is still paused and the saved answer is listed with this question. Check the
				decision outcome if needed, then choose Resume with this answer.
			</p>
		</div>
	{/if}
</section>
