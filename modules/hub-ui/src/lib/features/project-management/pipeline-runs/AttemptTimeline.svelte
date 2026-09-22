<script lang="ts">
	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';

	type Delivery = components['schemas']['ExecutionDeliveryRead'];
	type Reply = components['schemas']['ExecutionReplyRead'];
	type Entry =
		| { kind: 'request'; at: string | null; delivery: Delivery }
		| { kind: 'reply'; at: string; reply: Reply };

	let { runId, attemptId }: { runId: string; attemptId: string } = $props();

	let loading = $state(true);
	let failed = $state(false);
	let entries = $state<Entry[]>([]);

	const causes: Record<Delivery['cause'], string> = {
		initial: 'first request',
		silent: 'the agent stayed silent',
		quota: 'the agent hit its usage limit',
		resume: 'resumed by the operator'
	};

	onMount(async () => {
		const params = { path: { run_id: runId, attempt_id: attemptId } };
		try {
			const [deliveries, replies] = await Promise.all([
				api.GET('/api/v1/pipeline-runs/{run_id}/attempts/{attempt_id}/deliveries', { params }),
				api.GET('/api/v1/pipeline-runs/{run_id}/attempts/{attempt_id}/replies', { params })
			]);
			if (deliveries.error || replies.error) {
				failed = true;
				return;
			}
			const merged: Entry[] = [
				...(deliveries.data ?? []).map((delivery): Entry => ({
					kind: 'request',
					at: delivery.posted_at,
					delivery
				})),
				...(replies.data ?? []).map((reply): Entry => ({
					kind: 'reply',
					at: reply.replied_at,
					reply
				}))
			];
			// A request that was planned but never posted has no time yet and goes last.
			entries = merged.sort((a, b) => (a.at ?? '9999').localeCompare(b.at ?? '9999'));
		} catch {
			failed = true;
		} finally {
			loading = false;
		}
	});
</script>

{#if loading}
	<p class="text-[11px] text-muted-foreground">Loading requests and replies…</p>
{:else if failed}
	<p class="text-[11px] text-destructive">Failed to load requests and replies.</p>
{:else if entries.length === 0}
	<p class="text-[11px] text-muted-foreground">
		Nothing was sent for this attempt (the pull request was implemented outside the pipeline, or the
		request is still planned).
	</p>
{:else}
	<ol
		class="space-y-1.5 border-l border-border/70 pl-3 text-sm [overflow-wrap:anywhere] sm:text-xs"
	>
		{#each entries as entry (entry.kind === 'request' ? entry.delivery.id : entry.reply.id)}
			<li>
				{#if entry.kind === 'request'}
					<span class="font-semibold">Request #{entry.delivery.delivery_number}</span>
					<span class="text-muted-foreground">
						· {causes[entry.delivery.cause]} ·
						{entry.at ? new Date(entry.at).toLocaleString() : 'not posted yet'}
					</span>
				{:else}
					<span class="font-semibold">Reply from {entry.reply.author}</span>
					<span class="text-muted-foreground">· {new Date(entry.at).toLocaleString()}</span>
					{#if entry.reply.is_quota_limit}
						<span class="font-semibold text-amber-600 dark:text-amber-400">· usage limit</span>
					{/if}
					{#if entry.reply.excerpt}
						<p class="mt-0.5 whitespace-pre-wrap text-muted-foreground">{entry.reply.excerpt}</p>
					{/if}
				{/if}
			</li>
		{/each}
	</ol>
{/if}
