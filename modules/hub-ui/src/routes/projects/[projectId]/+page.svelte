<script lang="ts">
	import { page } from '$app/state';
	import ProjectDetailView from '$lib/features/project-management/projects/ProjectDetailView.svelte';
	import { projectTab } from '$lib/features/project-management/projects/project-tabs';
</script>

{#key page.params.projectId}
	<ProjectDetailView
		projectId={page.params.projectId ?? ''}
		tab={projectTab(page.url.searchParams.get('tab'))}
	/>
{/key}
