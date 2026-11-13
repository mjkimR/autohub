<script lang="ts">
	import { onMount, tick, type Snippet } from 'svelte';

	let {
		children,
		menuOpen,
		current
	}: {
		children: Snippet;
		menuOpen: boolean;
		current: string | null;
	} = $props();

	let viewport: HTMLElement;
	let content: HTMLDivElement;
	let above = $state(false);
	let below = $state(false);
	let mounted = false;
	let queued = false;
	let alignRequested = false;
	let lastHeight = 0;
	let lastActive: HTMLElement | null = null;

	function alignDestination(active: HTMLElement) {
		const bounds = viewport.getBoundingClientRect();
		const link = active.getBoundingClientRect();
		// Keep the focus ring inside the scrollport; change only this list's scroll position.
		const clearance = 4;
		if (link.top < bounds.top + clearance) viewport.scrollTop -= bounds.top + clearance - link.top;
		else if (link.bottom > bounds.bottom - clearance)
			viewport.scrollTop += link.bottom - bounds.bottom + clearance;
	}

	async function update(align = false) {
		alignRequested ||= align;
		if (!mounted || queued) return;
		queued = true;
		await tick();
		queued = false;
		if (!mounted) return;
		const height = viewport.clientHeight;
		const candidate = viewport.querySelector<HTMLElement>('[aria-current="page"]');
		const active =
			candidate && !candidate.closest('[hidden]') && candidate.getClientRects().length
				? candidate
				: null;
		if (height > 0 && active && (alignRequested || lastHeight === 0 || active !== lastActive))
			alignDestination(active);
		lastActive = active;
		alignRequested = false;
		lastHeight = height;
		// One CSS pixel avoids false edges from fractional scroll/size rounding.
		above = height > 0 && viewport.scrollTop > 1;
		below = height > 0 && viewport.scrollHeight - height - viewport.scrollTop > 1;
	}

	$effect(() => {
		void menuOpen;
		void current;
		void update(true);
	});

	onMount(() => {
		mounted = true;
		const resize = () => void update();
		const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(resize);
		observer?.observe(viewport);
		observer?.observe(content);
		// Also handles known content/visibility changes when ResizeObserver is unavailable.
		const mutations = new MutationObserver(resize);
		mutations.observe(content, { childList: true, subtree: true, attributes: true });
		window.addEventListener('resize', resize);
		void update(true);
		return () => {
			mounted = false;
			observer?.disconnect();
			mutations.disconnect();
			window.removeEventListener('resize', resize);
		};
	});
</script>

<div class="flex min-h-0 flex-1 flex-col" data-navigation-viewport>
	<div
		aria-hidden="true"
		data-navigation-cue="top"
		data-visible={above}
		class={['navigation-edge-cue pointer-events-none h-2 shrink-0', !above && 'invisible']}
	></div>
	<nav
		bind:this={viewport}
		class="-mx-1 min-h-0 flex-1 overflow-y-auto px-1"
		aria-label="Primary navigation"
		onscroll={() => void update()}
		onfocusin={(event) => {
			if (event.target instanceof HTMLElement) alignDestination(event.target);
		}}
	>
		<div bind:this={content} class="space-y-5 py-3">
			{@render children()}
		</div>
	</nav>
	<div
		aria-hidden="true"
		data-navigation-cue="bottom"
		data-visible={below}
		class={['navigation-edge-cue pointer-events-none h-2 shrink-0', !below && 'invisible']}
	></div>
</div>
