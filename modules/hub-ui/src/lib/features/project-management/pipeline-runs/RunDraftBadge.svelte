<script lang="ts">
	import type { components } from '$lib/api';
	import { Badge } from '$lib/components/ui/badge';
	import { awaitingReady, draftPresentation } from './pull-status';
	/** Beside a run's state badge in lists: the PR is Draft, so merging waits on marking it Ready. */
	let {
		run
	}: { run: Pick<components['schemas']['PipelineRunRead'], 'state' | 'pull_observation'> } =
		$props();
	const view = draftPresentation(true);
</script>

{#if awaitingReady(run)}
	<Badge variant={view.variant} data-run-draft title="Mark the PR Ready for review in GitHub">
		<view.icon aria-hidden="true" />Draft · mark Ready
	</Badge>
{/if}
