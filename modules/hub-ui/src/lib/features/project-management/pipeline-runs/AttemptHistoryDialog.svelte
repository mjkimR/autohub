<script lang="ts">
	import { onMount } from 'svelte';
	import AttemptTimeline from './AttemptTimeline.svelte';
	import { api, type components } from '$lib/api';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import {
		Dialog,
		DialogContent,
		DialogHeader,
		DialogTitle,
		DialogFooter,
		DialogDescription
	} from '$lib/components/ui/dialog';
	import { RefreshCw, GitBranch, Clock, ExternalLink, History, Key } from '@lucide/svelte';

	type PipelineRun = components['schemas']['PipelineRunRead'];
	type ExecutionAttempt = components['schemas']['ExecutionAttemptRead'];
	type RunSummary = components['schemas']['PipelineRunSummary'];
	let { run: selectedRun, onclose }: { run: PipelineRun; onclose: () => void } = $props();
	let loadingAttempts = $state(false);
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
		try {
			const res = await api.GET('/api/v1/pipeline-runs/{run_id}/attempts', {
				params: { path: { run_id: selectedRun.id } }
			});
			if (res.data?.items) {
				attempts = res.data.items;
				runSummary = res.data.summary;
			}
		} catch {
			toast.error('Failed to load execution attempts');
		} finally {
			loadingAttempts = false;
		}
	}

	onMount(() => {
		void loadAttempts();
	});
</script>

<!-- Attempts History Dialog -->
<Dialog
	open={true}
	onOpenChange={(open) => {
		if (!open) onclose();
	}}
>
	<DialogContent class="max-h-[90vh] overflow-y-auto sm:max-w-[650px]">
		<DialogHeader>
			<DialogTitle class="flex items-center gap-2">
				<History class="size-5 text-primary" />
				Execution Attempts
			</DialogTitle>
			<DialogDescription>
				Immutable snapshots, correlation keys, and external execution outcomes.
			</DialogDescription>
		</DialogHeader>

		<div class="space-y-4 py-2">
			{#if selectedRun}
				<div class="rounded-lg border border-border/80 bg-muted/20 p-3 text-xs">
					<div class="flex items-center justify-between font-semibold text-foreground">
						<span class="flex items-center gap-1.5 font-mono text-primary">
							<GitBranch class="size-3.5" />
							PR #{selectedRun.pull_number}: {selectedRun.pull_snapshot?.title || 'No title'}
						</span>
						<Badge variant="outline" class="font-mono">{selectedRun.state}</Badge>
					</div>
					<div class="mt-2 grid grid-cols-2 gap-2 text-muted-foreground">
						<div>
							Run ID: <span class="font-mono text-foreground">{selectedRun.id.slice(0, 8)}...</span>
						</div>
						<div>
							Working Branch: <span class="font-mono text-foreground">{selectedRun.branch}</span>
						</div>
					</div>
				</div>
			{/if}

			{#if loadingAttempts}
				<div class="flex h-32 items-center justify-center text-muted-foreground">
					<RefreshCw class="size-5 animate-spin" />
					<span class="ml-2 text-sm">Loading attempts...</span>
				</div>
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
						class="grid grid-cols-3 gap-2 rounded-lg border border-border/70 bg-muted/40 p-3 text-xs"
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
							<p class="col-span-3 text-amber-600 dark:text-amber-400">
								The agent reported its usage limit {runSummary.quota_limit_replies} time(s).
							</p>
						{/if}
					</div>
				{/if}
				<div class="space-y-3">
					{#each attempts as attempt (attempt.id)}
						<div class="space-y-2.5 rounded-lg border border-border/80 bg-card p-3.5 shadow-xs">
							<div class="flex items-center justify-between">
								<div class="flex items-center gap-2">
									<Badge variant="secondary" class="font-mono text-xs">
										Attempt #{attempt.attempt_number}
									</Badge>
									<span class="text-xs font-semibold text-muted-foreground uppercase">
										{attempt.kind}
									</span>
								</div>
								<Badge variant="outline" class="capitalize">
									{attempt.state}
								</Badge>
							</div>

							<div class="space-y-1 text-xs">
								<div class="flex items-center gap-1.5 text-muted-foreground">
									<Key class="size-3 shrink-0" />
									<span>Idempotency Key:</span>
									<span class="font-mono text-foreground">{attempt.idempotency_key}</span>
								</div>
								<div class="flex items-center gap-1.5 text-muted-foreground">
									<span>Digest:</span>
									<span class="font-mono text-[11px] text-foreground"
										>{attempt.request_digest.slice(0, 16)}...</span
									>
								</div>
								{#if attempt.conversation_url}
									<div class="flex items-center gap-1.5 pt-1 text-primary">
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
										class="mt-2 rounded-md border border-rose-500/30 bg-rose-500/10 p-2 text-rose-600 dark:text-rose-400"
									>
										<div class="font-semibold">{attempt.failure_code || 'Execution Error'}</div>
										<div class="text-[11px]">{attempt.failure_detail}</div>
									</div>
								{/if}
							</div>

							<div>
								<button
									type="button"
									class="text-[11px] text-primary hover:underline"
									onclick={() => (openTimelines[attempt.id] = !openTimelines[attempt.id])}
								>
									{openTimelines[attempt.id] ? 'Hide' : 'Show'} requests and replies
								</button>
								{#if openTimelines[attempt.id] && selectedRun}
									<div class="mt-2">
										<AttemptTimeline runId={selectedRun.id} attemptId={attempt.id} />
									</div>
								{/if}
							</div>

							<div
								class="flex items-center justify-between border-t border-border/50 pt-2 text-[10px] text-muted-foreground"
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

		<DialogFooter>
			<Button type="button" variant="outline" onclick={onclose}>Close</Button>
		</DialogFooter>
	</DialogContent>
</Dialog>
