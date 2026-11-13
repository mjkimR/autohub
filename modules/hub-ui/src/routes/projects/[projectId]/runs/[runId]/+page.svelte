<script lang="ts">
	import { page } from '$app/state';
	import RunPageView from '$lib/features/project-management/pipeline-runs/run-page/RunPageView.svelte';
</script>

{#key `${page.params.projectId}:${page.params.runId}`}
	<RunPageView projectId={page.params.projectId ?? ''} runId={page.params.runId ?? ''} />
{/key}
