<script lang="ts">
	import { Badge } from '$lib/components/ui/badge';
	import type { components } from '$lib/api';
	let {
		config,
		projectName
	}: { config: components['schemas']['ScheduleConfigRead']; projectName?: string } = $props();
	const kind = $derived(config.owner?.kind ?? 'operator');
	const projectId = $derived(config.owner?.project_id);
	const name = $derived(projectName || projectId);
	const label = $derived(
		kind === 'connection_test'
			? 'Project connections'
			: kind === 'project_agent_schedule'
				? 'Agent schedules'
				: 'Project automation'
	);
	const tab = $derived(kind === 'connection_test' ? 'connections' : 'automation');
</script>

{#if kind !== 'operator'}
	<Badge variant="info"
		>{kind === 'system_maintenance' ? 'System Managed' : 'Project Managed'}</Badge
	>
	{#if projectId}
		<div class="text-xs text-muted-foreground">{name}</div>
		<a
			class="text-xs font-medium underline-offset-4 hover:underline"
			href={`/projects/${encodeURIComponent(projectId)}?tab=${tab}`}
			aria-label={`${label} for ${name}`}>{label}</a
		>
	{:else if kind !== 'system_maintenance'}
		<span class="text-xs text-muted-foreground">Owner unavailable</span>
	{/if}
{/if}
