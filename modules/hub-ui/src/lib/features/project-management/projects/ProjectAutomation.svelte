<script lang="ts">
	import type { components } from '$lib/api';
	import AgentSchedulesPanel from '../agent-schedules/AgentSchedulesPanel.svelte';
	import OwnedSchedules from './OwnedSchedules.svelte';
	import ProjectSettingsForm from './ProjectSettingsForm.svelte';

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
</script>

<div class="space-y-6">
	<section
		id="development-automation"
		aria-labelledby="development-automation-heading"
		class="space-y-4 rounded-xl border bg-card p-4 sm:p-6"
	>
		<div class="space-y-1">
			<h2 id="development-automation-heading" class="text-lg font-semibold">
				Development automation
			</h2>
			<p class="max-w-prose text-sm text-muted-foreground">
				How PR runs merge, recover and get dispatched. The dispatch interval drives the project's
				dispatch schedule below.
			</p>
		</div>
		{#if project.github}
			<!-- A narrow column keeps each toggle beside the setting it changes. -->
			<div class="max-w-2xl">
				<ProjectSettingsForm {project} {connectors} {catalogs} section="automation" {onsaved} />
			</div>
		{:else}
			<p class="text-sm text-muted-foreground">Add a GitHub connection first.</p>
		{/if}
	</section>

	<section
		aria-labelledby="project-schedules-heading"
		class="space-y-4 rounded-xl border bg-card p-4 sm:p-6"
	>
		<div class="space-y-1">
			<h2 id="project-schedules-heading" class="text-lg font-semibold">Schedules</h2>
			<p class="max-w-prose text-sm text-muted-foreground">
				Every scheduler entry this project owns. Agent schedules follow in their own section.
			</p>
		</div>
		<OwnedSchedules {project} />
	</section>

	<AgentSchedulesPanel {project} {catalogs} />
</div>
