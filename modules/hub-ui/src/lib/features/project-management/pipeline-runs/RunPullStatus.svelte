<script lang="ts">
	import type { components } from '$lib/api';
	import { Badge } from '$lib/components/ui/badge';
	import {
		draftPresentation,
		newerHead,
		verificationPresentation,
		type LaterHead
	} from './pull-status';
	/**
	 * Last observed Draft and CI status of the run's PR (CAP-PR-pull-request-delivery, "Observed PR
	 * status read"). It is retained Hub state, not a live GitHub read, and can describe an older head.
	 */
	let {
		run,
		later = []
	}: {
		run: components['schemas']['PipelineRunRead'];
		/** Heads Hub saw after the observation, used to flag it as stale. */
		later?: LaterHead[];
	} = $props();
	let observation = $derived(run.pull_observation ?? null);
	let draft = $derived(observation ? draftPresentation(observation.draft) : null);
	let verification = $derived(
		observation ? verificationPresentation(observation.verification) : null
	);
	let newer = $derived(observation ? newerHead(observation, later) : null);
	const time = (value: string) => new Date(value).toLocaleString();
</script>

<div aria-label="PR status" role="group" class="space-y-1 text-sm">
	<div class="flex flex-wrap items-center gap-x-2 gap-y-1">
		<span class="text-xs text-muted-foreground">PR status</span>
		{#if observation && draft && verification}
			<Badge variant={draft.variant}><draft.icon aria-hidden="true" />{draft.label}</Badge>
			<Badge variant={verification.variant}
				><verification.icon aria-hidden="true" />{verification.label}</Badge
			>
			<span class="text-xs text-muted-foreground"
				>head <code class="text-foreground">{observation.head_sha.slice(0, 8)}</code> · observed {time(
					observation.observed_at
				)}</span
			>
		{:else}
			<span class="text-muted-foreground">Not observed yet</span>
		{/if}
	</div>
	{#if observation && newer}
		<p class="text-xs text-muted-foreground">
			Observed on an earlier head; head <code class="text-foreground">{newer.slice(0, 8)}</code> is newer
			and has not been observed yet.
		</p>
	{/if}
	{#if observation?.reason}<p class="max-w-prose text-xs break-words text-muted-foreground">
			{observation.reason}
		</p>{/if}
</div>
