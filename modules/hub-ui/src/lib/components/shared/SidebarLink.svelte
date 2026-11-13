<script lang="ts">
	import type { Component, Snippet } from 'svelte';

	let {
		href,
		label,
		icon: Icon,
		active,
		trailing
	}: {
		href: string;
		label: string;
		icon: Component<{ class?: string }>;
		active: boolean;
		trailing?: Snippet;
	} = $props();

	let link = $state<HTMLAnchorElement>();
	// Keep the current destination visible when the sidebar list overflows (e.g. administrative links).
	$effect(() => {
		if (active) link?.scrollIntoView?.({ block: 'nearest' });
	});
</script>

<!--
	Active is ink, not hue: a 1px sidebar-ring outline (3:1 or better in both themes) on the
	accent fill, plus semibold text and aria-current. The left rule stays reserved for attention.
-->
<a
	bind:this={link}
	{href}
	aria-current={active ? 'page' : undefined}
	data-active={active ? 'true' : undefined}
	class={[
		'flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors outline-none focus-visible:ring-3 focus-visible:ring-sidebar-ring/50',
		active
			? 'bg-sidebar-accent font-semibold text-sidebar-accent-foreground inset-ring inset-ring-sidebar-ring'
			: 'font-medium text-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground'
	]}
>
	<Icon class="size-4 shrink-0" />
	<span class="min-w-0 flex-1 truncate">{label}</span>
	{@render trailing?.()}
</a>
