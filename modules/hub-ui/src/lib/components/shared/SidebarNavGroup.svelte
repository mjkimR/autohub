<script lang="ts">
	import { untrack, type Snippet } from 'svelte';
	import { ChevronRight } from '@lucide/svelte';
	import {
		groupHolds,
		readGroupOpen,
		writeGroupOpen,
		type NavGroup,
		type NavItem
	} from '$lib/components/shared/app-shell-nav';

	let {
		group,
		current,
		link
	}: {
		group: NavGroup;
		/** The nav href of the current page, or null outside the navigation. */
		current: string | null;
		link: Snippet<[NavItem]>;
	} = $props();

	const headingId = $derived(`nav-group-${group.id}-label`);
	const listId = $derived(`nav-group-${group.id}`);
	const holdsCurrent = $derived(groupHolds(group, current));

	// A collapsible group opens for the page it holds; a toggle on this page overrides that until the
	// operator navigates, and the last toggle is remembered for this browser.
	// The group identity is fixed for the component's lifetime; read storage once.
	let remembered = $state(untrack(() => readGroupOpen(group.id)));
	let choice = $state<{ current: string | null; open: boolean } | null>(null);
	const open = $derived(
		!group.collapsible || (choice?.current === current ? choice.open : remembered || holdsCurrent)
	);

	function toggle() {
		const next = !open;
		choice = { current, open: next };
		remembered = next;
		writeGroupOpen(group.id, next);
	}
</script>

<div>
	{#if group.collapsible}
		<button
			type="button"
			id={headingId}
			aria-expanded={open}
			aria-controls={listId}
			onclick={toggle}
			class={[
				// The taller hit area is pulled into the heading rhythm so it lines up with static labels.
				'-mt-3 -mb-2 flex min-h-11 w-full items-center gap-2 rounded-lg px-3 text-xs font-semibold tracking-wider uppercase transition-colors outline-none hover:text-sidebar-foreground focus-visible:ring-3 focus-visible:ring-sidebar-ring/50 lg:-mt-2 lg:mb-0 lg:min-h-8',
				!open && holdsCurrent ? 'text-sidebar-foreground' : 'text-muted-foreground'
			]}
		>
			<span>{group.label}</span>
			{#if !open && holdsCurrent}
				<span
					aria-hidden="true"
					class="size-1.5 rounded-full bg-sidebar-foreground"
					data-holds-current
				></span>
				<span class="sr-only">, contains the current page</span>
			{/if}
			<ChevronRight
				aria-hidden="true"
				class={[
					'ml-auto size-3.5 shrink-0 transition-transform motion-reduce:transition-none',
					open && 'rotate-90'
				]}
			/>
		</button>
	{:else}
		<p
			id={headingId}
			class="px-3 pb-1.5 text-xs font-semibold tracking-wider text-muted-foreground uppercase"
		>
			{group.label}
		</p>
	{/if}
	<div
		id={listId}
		role="group"
		aria-labelledby={headingId}
		hidden={!open}
		class="space-y-1"
		data-nav-group={group.id}
	>
		{#each group.items as item (item.href)}
			{@render link(item)}
		{/each}
	</div>
</div>
