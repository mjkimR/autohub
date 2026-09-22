<script lang="ts">
	import type { components } from '$lib/api';
	import { Button } from '$lib/components/ui/button';
	import ProjectSettingsForm from './ProjectSettingsForm.svelte';
	import ProjectConnectionCheckDialog from './ProjectConnectionCheckDialog.svelte';
	import ConnectionTestsPanel from './ConnectionTestsPanel.svelte';
	let {
		project,
		connectors,
		catalogs,
		onsaved
	}: {
		project: components['schemas']['ProjectRead'];
		connectors: components['schemas']['ConnectorRead'][];
		catalogs: components['schemas']['AICatalogRead'][];
		onsaved: () => void;
	} = $props();
	let checkOpen = $state(false);
</script>

<div class="space-y-6">
	<section class="rounded-xl border bg-card p-6">
		<h2 class="text-lg font-semibold">GitHub connection</h2>
		<ProjectSettingsForm {project} {connectors} {catalogs} {onsaved} section="connection" />
		{#if project.github}
			<div class="mt-4 flex flex-wrap items-center justify-between gap-3 border-t pt-4">
				<p class="text-sm text-muted-foreground">
					Checks repository, CI access and the account used to post mentions.
				</p>
				<Button variant="outline" onclick={() => (checkOpen = true)}>GitHub access check</Button>
			</div>
		{/if}
	</section>
	<ConnectionTestsPanel {project} {catalogs} />
</div>
{#if checkOpen}
	<ProjectConnectionCheckDialog {project} onclose={() => (checkOpen = false)} onchecked={onsaved} />
{/if}
