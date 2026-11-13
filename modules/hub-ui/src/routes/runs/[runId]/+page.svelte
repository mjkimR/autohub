<script lang="ts">
	import { page } from '$app/state';
	import RunRedirect from '$lib/features/project-management/pipeline-runs/run-page/RunRedirect.svelte';
</script>

{#key page.params.runId}
	<RunRedirect runId={page.params.runId ?? ''} />
{/key}
