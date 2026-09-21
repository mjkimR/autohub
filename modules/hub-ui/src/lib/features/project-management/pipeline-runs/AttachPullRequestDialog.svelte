<script lang="ts">
	import { onMount } from 'svelte';
	import { api, type components } from '$lib/api';
	import { apiErrorMessage } from '$lib/api/errors';
	import { toast } from 'svelte-sonner';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import {
		Dialog,
		DialogContent,
		DialogHeader,
		DialogTitle,
		DialogFooter,
		DialogDescription
	} from '$lib/components/ui/dialog';
	import { Link2 } from '@lucide/svelte';

	type PipelineRun = components['schemas']['PipelineRunRead'];
	let {
		run: attachTargetRun,
		onclose,
		onsaved
	}: { run: PipelineRun; onclose: () => void; onsaved: () => void } = $props();
	let isAttachingPr = $state(false);
	let attachPullNumber = $state<number>(1);
	let attachPullUrl = $state('');

	onMount(() => {
		attachPullNumber = attachTargetRun.pull_number || 1;
		attachPullUrl = attachTargetRun.pull_url || '';
	});
	async function handleAttachPrSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!attachTargetRun) return;
		isAttachingPr = true;
		try {
			const res = await api.POST('/api/v1/pipeline-runs/{run_id}/attach-pr', {
				params: { path: { run_id: attachTargetRun.id } },
				body: {
					pull_number: Number(attachPullNumber),
					pull_url: attachPullUrl.trim() || null
				}
			});
			if (res.error) {
				const detail = apiErrorMessage(res.error, 'Failed to attach PR');
				toast.error(detail);
			} else {
				toast.success(`PR #${attachPullNumber} attached!`);
				onclose();
				onsaved();
			}
		} catch {
			toast.error('Error attaching PR');
		} finally {
			isAttachingPr = false;
		}
	}
</script>

<!-- Attach PR Dialog -->
<Dialog
	open={true}
	onOpenChange={(open) => {
		if (!open) onclose();
	}}
>
	<DialogContent class="sm:max-w-[450px]">
		<DialogHeader>
			<div class="flex items-center gap-2">
				<div class="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
					<Link2 class="size-4" />
				</div>
				<div>
					<DialogTitle>Attach Pull Request</DialogTitle>
					<DialogDescription>
						Associate an open GitHub PR with run <span class="font-semibold text-foreground"
							>PR #{attachTargetRun?.pull_number}</span
						>.
					</DialogDescription>
				</div>
			</div>
		</DialogHeader>

		<form onsubmit={handleAttachPrSubmit} class="space-y-4 py-2">
			<div class="space-y-1.5">
				<label for="attachPRNum" class="text-xs font-semibold text-muted-foreground uppercase">
					Pull Request Number
				</label>
				<Input
					id="attachPRNum"
					type="number"
					min="1"
					bind:value={attachPullNumber}
					placeholder="e.g. 42"
					required
				/>
			</div>

			<div class="space-y-1.5">
				<label for="attachPRUrl" class="text-xs font-semibold text-muted-foreground uppercase">
					Pull Request URL (optional)
				</label>
				<Input
					id="attachPRUrl"
					type="url"
					bind:value={attachPullUrl}
					placeholder="https://github.com/owner/repo/pull/42"
				/>
			</div>

			<DialogFooter class="pt-2">
				<Button type="button" variant="outline" onclick={onclose}>Cancel</Button>
				<Button type="submit" disabled={isAttachingPr}>
					{isAttachingPr ? 'Attaching...' : 'Attach PR'}
				</Button>
			</DialogFooter>
		</form>
	</DialogContent>
</Dialog>
