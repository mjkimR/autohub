<script lang="ts">
	import { onMount } from 'svelte';
	import AttemptTimeline from './AttemptTimeline.svelte';
	import { attemptStateLabel } from './presentation';
	import { api, type components } from '$lib/api';
	import LoadError from '$lib/components/shared/LoadError.svelte';
	import { responseData } from '$lib/api/pagination';
	import { Badge } from '$lib/components/ui/badge';
	import { Clock, ExternalLink, Key } from '@lucide/svelte';

	type ExecutionAttempt = components['schemas']['ExecutionAttemptRead'];
	type RunSummary = components['schemas']['PipelineRunSummary'];
	/** Execution attempts of one PR run: aggregate summary, then each attempt and its timeline. */
	let { runId }: { runId: string } = $props();
	let loadingAttempts = $state(false);
	let loadError = $state('');
	let attempts = $state<ExecutionAttempt[]>([]);
	let runSummary = $state<RunSummary | null>(null);
	// Attempts whose requests and replies are shown; loaded when first opened.
	let openTimelines = $state<Record<string, boolean>>({});

	function summarizeKinds(kinds: Record<string, number>) {
		return Object.entries(kinds)
			.map(([kind, count]) => `${count} ${kind}`)
			.join(', ');
	}

	function formatElapsed(seconds: number) {
		if (seconds < 3600) return `${Math.max(1, Math.round(seconds / 60))} min`;
		const hours = Math.floor(seconds / 3600);
		return hours < 48
			? `${hours} h ${Math.round((seconds % 3600) / 60)} min`
			: `${Math.round(hours / 24)} days`;
	}

	async function loadAttempts() {
		attempts = [];
		runSummary = null;
		openTimelines = {};
		loadingAttempts = true;
		loadError = '';
		try {
			const res = await api.GET('/api/v1/pipeline-runs/{run_id}/attempts', {
				params: { path: { run_id: runId } }
			});
			const data = responseData(res, 'Failed to load execution attempts');
			attempts = data.items;
			runSummary = data.summary;
		} catch (error) {
			loadError = error instanceof Error ? error.message : 'Failed to load execution attempts';
		} finally {
			loadingAttempts = false;
		}
	}

	onMount(() => {
		void loadAttempts();
	});
</script>

<div class="space-y-4">
	{#if loadingAttempts}
		<p role="status" class="flex h-32 items-center justify-center text-sm text-muted-foreground">
			Loading attempts...
		</p>
	{:else if loadError}
		<LoadError message={loadError} retry={loadAttempts} />
	{:else if attempts.length === 0}
		<div
			class="flex flex-col items-center justify-center gap-2 rounded-lg border border-border/70 p-6 text-center text-muted-foreground"
		>
			<Clock class="size-8 text-muted-foreground/40" />
			<span>No execution attempts recorded yet</span>
			<p class="text-xs text-muted-foreground/80">
				An attempt is prepared when the dispatcher acquires a lease for this run.
			</p>
		</div>
	{:else}
		{#if runSummary}
			<div
				class="grid grid-cols-1 gap-2 rounded-lg border border-border/70 bg-muted/40 p-3 text-xs sm:grid-cols-3"
			>
				<div>
					<p class="font-semibold text-muted-foreground uppercase">Agent requests</p>
					<p class="text-sm font-medium">{runSummary.requests_sent} sent</p>
				</div>
				<div>
					<p class="font-semibold text-muted-foreground uppercase">Attempts</p>
					<p class="text-sm font-medium">{summarizeKinds(runSummary.attempts_by_kind)}</p>
				</div>
				<div>
					<p class="font-semibold text-muted-foreground uppercase">
						{runSummary.finished_at ? 'Took' : 'Running for'}
					</p>
					<p class="text-sm font-medium">{formatElapsed(runSummary.elapsed_seconds)}</p>
				</div>
				{#if runSummary.quota_limit_replies > 0}
					<p class="text-warning sm:col-span-3">
						The agent reported its usage limit {runSummary.quota_limit_replies} time(s).
					</p>
				{/if}
			</div>
		{/if}
		<div class="space-y-3">
			{#each attempts as attempt (attempt.id)}
				<div class="space-y-2.5 rounded-lg border border-border/80 bg-card p-3.5 shadow-xs">
					<div class="flex flex-wrap items-center justify-between gap-2">
						<div class="flex flex-wrap items-center gap-2">
							<Badge variant="secondary" class="font-mono text-xs">
								Attempt #{attempt.attempt_number}
							</Badge>
							<span class="text-xs font-semibold text-muted-foreground uppercase">
								{attempt.kind}
							</span>
						</div>
						<Badge variant="outline">
							{attemptStateLabel(attempt.state)}
						</Badge>
					</div>

					<div class="space-y-1 text-xs">
						<div class="flex min-w-0 flex-wrap items-center gap-1.5 text-muted-foreground">
							<Key class="size-3 shrink-0" />
							<span>Idempotency Key:</span>
							<span class="font-mono text-foreground">{attempt.idempotency_key}</span>
						</div>
						<div class="flex min-w-0 flex-wrap items-center gap-1.5 text-muted-foreground">
							<span>Digest:</span>
							<span class="font-mono text-xs text-foreground"
								>{attempt.request_digest.slice(0, 16)}...</span
							>
						</div>
						{#if attempt.conversation_url}
							<div class="flex min-w-0 flex-wrap items-center gap-1.5 pt-1 text-primary">
								<ExternalLink class="size-3 shrink-0" />
								<a
									href={attempt.conversation_url}
									target="_blank"
									rel="noreferrer"
									class="hover:underline"
								>
									Codex Cloud Conversation
								</a>
							</div>
						{/if}
						{#if attempt.failure_code || attempt.failure_detail}
							<div
								class="mt-2 rounded-md border border-destructive/30 bg-destructive/10 p-2 text-destructive"
							>
								<div class="font-semibold">{attempt.failure_code || 'Execution Error'}</div>
								<div class="text-sm whitespace-pre-wrap">{attempt.failure_detail}</div>
							</div>
						{/if}
					</div>

					<div>
						<button
							type="button"
							aria-expanded={!!openTimelines[attempt.id]}
							class="h-8 text-sm text-primary hover:underline"
							onclick={() => (openTimelines[attempt.id] = !openTimelines[attempt.id])}
						>
							{openTimelines[attempt.id] ? 'Hide' : 'Show'} requests and replies
						</button>
						{#if openTimelines[attempt.id]}
							<div class="mt-2">
								<AttemptTimeline {runId} attemptId={attempt.id} />
							</div>
						{/if}
					</div>

					<div
						class="flex flex-wrap items-center justify-between gap-2 border-t border-border/50 pt-2 text-xs text-muted-foreground"
					>
						<span>Created: {new Date(attempt.created_at).toLocaleString()}</span>
						{#if attempt.finished_at}
							<span>Finished: {new Date(attempt.finished_at).toLocaleTimeString()}</span>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
