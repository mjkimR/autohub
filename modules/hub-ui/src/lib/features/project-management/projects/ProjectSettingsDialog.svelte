<script lang="ts">
	import type { components } from '$lib/api';
	import {
		Dialog,
		DialogContent,
		DialogHeader,
		DialogTitle,
		DialogDescription
	} from '$lib/components/ui/dialog';
	import ProjectSettingsForm from './ProjectSettingsForm.svelte';
	let {
		project,
		connectors,
		catalogs,
		onclose,
		onsaved
	}: {
		project: components['schemas']['ProjectRead'];
		connectors: components['schemas']['ConnectorRead'][];
		catalogs: components['schemas']['AICatalogRead'][];
		onclose: () => void;
		onsaved: () => void;
	} = $props();
</script>

<Dialog
	open
	onOpenChange={(open) => {
		if (!open) onclose();
	}}
>
	<!-- eslint-disable-next-line shadcn/no-arbitrary-values -- viewport-relative dialog height cap has no scale equivalent -->
	<DialogContent class="max-h-[90vh] overflow-y-auto sm:max-w-175">
		<DialogHeader
			><DialogTitle>Project Settings</DialogTitle><DialogDescription
				>Configure this project.</DialogDescription
			></DialogHeader
		>
		<ProjectSettingsForm
			{project}
			{connectors}
			{catalogs}
			onsaved={() => {
				onclose();
				onsaved();
			}}
		/>
	</DialogContent>
</Dialog>
