<script lang="ts">
	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Badge } from '$lib/components/ui/badge';
	import {
		Dialog,
		DialogContent,
		DialogHeader,
		DialogTitle,
		DialogFooter,
		DialogDescription
	} from '$lib/components/ui/dialog';
	import {
		RefreshCw,
		CheckCircle2,
		XCircle,
		Activity,
		ExternalLink,
		AlertCircle,
		MinusCircle,
		CheckCheck
	} from '@lucide/svelte';

	type Project = components['schemas']['ProjectRead'];
	type ConnectionCheck = components['schemas']['ConnectionCheck'];
	let {
		project: checkingProject,
		onclose,
		onchecked
	}: { project: Project; onclose: () => void; onchecked: () => void } = $props();
	let isChecking = $state(false);
	let checkPullNumber = $state<number>(1);
	let checkResult = $state<ConnectionCheck | null>(null);
	onMount(() => {
		checkResult = checkingProject.last_check || null;
	});
	async function runConnectionCheck() {
		if (!checkingProject) return;
		isChecking = true;
		try {
			const res = await api.POST('/api/v1/projects/{project_id}/check', {
				params: { path: { project_id: checkingProject.id } },
				body: { pull_number: Number(checkPullNumber) }
			});

			if (res.error) {
				const detail = apiErrorMessage(res.error, 'Connection check failed');
				toast.error(detail);
			} else if (res.data) {
				checkResult = res.data;
				if (res.data.ready) {
					toast.success('GitHub and CI access check passed. Use the PR test to verify Codex.');
				} else {
					toast.warning('Connection check completed with issues.');
				}
				onchecked();
			}
		} catch {
			toast.error('An error occurred during connection check');
		} finally {
			isChecking = false;
		}
	}
</script>

<!-- Connection Check Dialog -->
<Dialog
	open={true}
	onOpenChange={(open) => {
		if (!open) onclose();
	}}
>
	<DialogContent class="max-h-[90vh] overflow-y-auto sm:max-w-[600px]">
		<DialogHeader>
			<DialogTitle class="flex items-center gap-2">
				<Activity class="size-5 text-primary" />
				Connection & CI Check
			</DialogTitle>
			<DialogDescription>
				Verify read access to GitHub repository, active CI workflow, and evaluate PR checks.
			</DialogDescription>
		</DialogHeader>

		<div class="space-y-4 py-2">
			{#if checkingProject}
				<div
					class="flex items-center justify-between rounded-lg border border-border/70 bg-muted/30 p-3"
				>
					<div>
						<div class="font-semibold text-foreground">{checkingProject.name}</div>
						<div class="font-mono text-xs text-muted-foreground">
							{checkingProject.github?.repository || 'No GitHub configured'}
						</div>
					</div>
					<div class="flex items-center gap-2">
						<div class="flex items-center gap-1.5">
							<span class="text-xs font-semibold text-muted-foreground">PR #</span>
							<Input
								type="number"
								min="1"
								bind:value={checkPullNumber}
								class="h-8 w-20 text-xs"
								disabled={isChecking}
							/>
						</div>
						<Button size="sm" onclick={runConnectionCheck} disabled={isChecking} class="gap-1.5">
							<RefreshCw class="size-3.5 {isChecking ? 'animate-spin' : ''}" />
							{isChecking ? 'Checking...' : 'Run Check'}
						</Button>
					</div>
				</div>
			{/if}

			{#if checkResult}
				<!-- Overall status -->
				<div
					class="flex items-center justify-between rounded-lg border p-3 {checkResult.ready
						? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
						: 'border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400'}"
				>
					<div class="flex items-center gap-2">
						{#if checkResult.ready}
							<CheckCheck class="size-5" />
							<span class="font-semibold">Ready for CI Observation</span>
						{:else}
							<AlertCircle class="size-5" />
							<span class="font-semibold">Check Incomplete or Failed</span>
						{/if}
					</div>
					<span class="font-mono text-xs text-muted-foreground">
						{new Date(checkResult.checked_at).toLocaleTimeString()}
					</span>
				</div>

				<!-- Individual Checks -->
				<div class="space-y-2">
					<span class="text-xs font-semibold text-muted-foreground uppercase"
						>Verification Items</span
					>
					<div class="divide-y divide-border/60 rounded-lg border border-border/80 bg-card">
						{#each checkResult.checks as check (check.name)}
							<div class="flex items-start justify-between p-3">
								<div class="space-y-0.5">
									<div class="text-sm font-medium text-foreground">{check.name}</div>
									<div class="text-xs text-muted-foreground">{check.detail}</div>
								</div>
								<div>
									{#if check.status === 'passed'}
										<Badge
											variant="default"
											class="gap-1 bg-emerald-500/15 text-emerald-600 hover:bg-emerald-500/25 dark:text-emerald-400"
										>
											<CheckCircle2 class="size-3" />
											Passed
										</Badge>
									{:else if check.status === 'failed'}
										<Badge
											variant="destructive"
											class="gap-1 bg-rose-500/15 text-rose-600 hover:bg-rose-500/25 dark:text-rose-400"
										>
											<XCircle class="size-3" />
											Failed
										</Badge>
									{:else}
										<Badge variant="secondary" class="gap-1 text-muted-foreground">
											<MinusCircle class="size-3" />
											Skipped
										</Badge>
									{/if}
								</div>
							</div>
						{/each}
					</div>
				</div>

				<!-- PR Observation Details if available -->
				{#if checkResult.observation?.pulls?.[0]}
					{@const pull = checkResult.observation.pulls[0]}
					<div class="space-y-2 rounded-lg border border-border/70 bg-muted/20 p-3 text-xs">
						<div class="flex items-center justify-between font-semibold text-foreground">
							<span>PR #{pull.number} Verification Detail</span>
							<a
								href={pull.url}
								target="_blank"
								rel="noreferrer"
								class="inline-flex items-center gap-1 text-primary hover:underline"
							>
								View on GitHub
								<ExternalLink class="size-3" />
							</a>
						</div>
						<div class="grid grid-cols-2 gap-2 text-muted-foreground">
							<div>Head: <span class="font-mono">{pull.head_sha.slice(0, 7)}</span></div>
							<div>
								Status: <span class="font-semibold text-foreground capitalize"
									>{pull.result.status}</span
								>
							</div>
						</div>
						{#if pull.result.reason}
							<div class="text-muted-foreground">
								Reason: <span class="text-foreground">{pull.result.reason}</span>
							</div>
						{/if}
					</div>
				{/if}
			{/if}
		</div>

		<DialogFooter>
			<Button type="button" variant="outline" onclick={onclose}>Close</Button>
		</DialogFooter>
	</DialogContent>
</Dialog>
