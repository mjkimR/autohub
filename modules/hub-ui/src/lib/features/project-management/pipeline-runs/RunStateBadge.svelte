<script lang="ts">
	import type { components } from '$lib/api';
	import { Badge } from '$lib/components/ui/badge';
	import { cn } from '$lib/utils';
	import { getRunStatePresentation } from './presentation';

	type RunState = components['schemas']['PipelineRunState'];

	let { state, class: className }: { state: RunState; class?: string } = $props();

	const view = $derived(getRunStatePresentation(state));
</script>

<Badge variant={view.variant} data-run-state={state} class={cn('capitalize', className)}>
	<view.icon aria-hidden="true" />
	{view.label}
</Badge>
