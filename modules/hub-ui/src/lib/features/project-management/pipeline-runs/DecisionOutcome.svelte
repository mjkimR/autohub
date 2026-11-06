<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { decisionIntent } from './decision-intents.svelte';
	let {
		runId,
		head,
		revision,
		terminal = false,
		onrefresh,
		recovery = false,
		onreconcile
	}: {
		runId: string;
		head: string;
		revision: number;
		terminal?: boolean;
		onrefresh: () => void | Promise<void>;
		recovery?: boolean;
		onreconcile?: () => void | Promise<void>;
	} = $props();
	let review = $derived(decisionIntent(runId, recovery));
	let outcome = $derived(review.outcome);
	let changed = $derived(
		!!review.intent &&
			(review.intent.head !== head || (!!outcome && outcome.run_revision !== revision))
	);
	async function read() {
		try {
			await review.check();
		} catch {
			/* retained error */
		}
	}
	async function retry() {
		try {
			await review.retry(head);
			await onrefresh();
		} catch {
			/* retained error */
		}
	}
</script>

<section class="space-y-2 rounded-lg border p-3 text-sm" aria-label="Decision outcome">
	<p class="font-medium">Decision outcome</p>
	{#if review.subject || review.intent || outcome}
		<p>
			Request <code>{review.subject?.requestId}</code> · {review.subject?.operation}
		</p>
		<p>
			{review.displayingIntent && review.intent?.acknowledged
				? 'Recorded'
				: outcome?.record_state === 'recorded'
					? 'Recorded evidence found'
					: 'Outcome unknown'}
		</p>
		{#if review.displayingIntent && review.intent?.operation === 'answer' && review.intent?.acknowledged}<p
			>
				Answer saved. The run remains stopped until explicit resume.
			</p>{/if}
		{#if review.displayingIntent && review.intent?.operation === 'answer' && 'answer' in review.intent.body}<p
				class="whitespace-pre-wrap"
			>
				{review.intent.body.answer}
			</p>{/if}
		{#if outcome?.answer_text}<p class="whitespace-pre-wrap">{outcome.answer_text}</p>{/if}
		{#if outcome?.applied_attempt_id}<p>
				Applied to attempt <code>{outcome.applied_attempt_id}</code>
			</p>{/if}
		{#if outcome?.delivery_state}<p>Delivery: {outcome.delivery_state}</p>{/if}
		{#if outcome?.publication_state}<p>
				{outcome.publication_state === 'pending'
					? 'Answer recorded — publication pending'
					: `Publication: ${outcome.publication_state}`}
			</p>{/if}
		{#if outcome?.candidate_heads?.length}<p>
				Retained candidates: {outcome.candidate_heads.join(', ')}
			</p>{/if}
		{#if outcome?.resolved_envelope}<p>Published envelope: {outcome.resolved_envelope}</p>{/if}
		{#if outcome}<p>
				Current run: {outcome.run_state}. Authority: {outcome.current_authority
					? 'Recorded at current inspection'
					: 'Unavailable'}
			</p>{/if}
		{#if changed}<p>Context changed. Review current context before another action.</p>{/if}
		<Button size="sm" variant="outline" disabled={review.busy} onclick={read}>Check outcome</Button>
		{#if review.unresolved && !review.intent?.rejected}<p>
				Original unresolved request: {review.intent?.requestId}
			</p>
			<Button
				size="sm"
				variant="outline"
				disabled={review.busy || terminal || changed}
				onclick={retry}>Retry same request</Button
			>{/if}
	{:else}
		<p class="text-muted-foreground">
			After a browser reload, unacknowledged submission intent is unavailable. Review durable owner
			history; an absent record leaves the outcome unknown.
		</p>
	{/if}
	{#if review.intent?.rejected}<Button
			variant="outline"
			onclick={async () => {
				await onrefresh();
				review.releaseRejection();
			}}>Review current context to correct input</Button
		>{/if}
	{#if onreconcile && !terminal && ((review.intent?.body as { decision?: string })?.decision === 'accept_plan' || (review.intent?.body as { decision?: string })?.decision === 'reject_plan' || ['accept_plan', 'reject_plan'].includes(outcome?.native_channel || ''))}
		<p>
			Reconcile publication inspects current evidence and may continue this run. It grants no
			approval and preserves later stops.
		</p>
		<Button variant="outline" disabled={review.busy} onclick={onreconcile}
			>Review publication reconciliation</Button
		>
	{/if}
	{#if review.error}<p role="status">{review.error}</p>{/if}
</section>
