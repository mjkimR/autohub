<script lang="ts">
	import ChevronDownIcon from '@lucide/svelte/icons/chevron-down';
	import { cn, type WithElementRef } from '$lib/utils.js';
	import type { HTMLSelectAttributes } from 'svelte/elements';

	type NativeSelectProps = Omit<WithElementRef<HTMLSelectAttributes, HTMLSelectElement>, 'size'> & {
		size?: 'sm' | 'default';
	};

	let {
		ref = $bindable(null),
		value = $bindable(),
		class: className,
		size = 'default',
		children,
		...restProps
	}: NativeSelectProps = $props();

	// A list box (`multiple`) shows its options inline, so it grows and drops the chevron.
	const multiple = $derived(Boolean(restProps.multiple));
</script>

<!-- `class` lands on the wrapper: callers pass layout (width, margin); the select fills it.
     A span keeps the markup valid inside a <label>; like a native select it is inline (pass `flex` for a block). -->
<span
	class={cn(
		'group/native-select relative inline-flex w-fit align-middle has-[select:disabled]:opacity-50',
		className
	)}
	data-slot="native-select-wrapper"
	data-size={size}
>
	<select
		bind:value
		bind:this={ref}
		data-slot="native-select"
		data-size={size}
		class={cn(
			'h-8 w-full min-w-0 appearance-none rounded-lg border border-input bg-transparent bg-none py-1 pr-8 pl-2.5 text-base transition-colors outline-none select-none selection:bg-primary selection:text-primary-foreground placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-not-allowed aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 data-[size=sm]:h-7 data-[size=sm]:rounded-[min(var(--radius-md),10px)] data-[size=sm]:py-0.5 md:text-sm dark:bg-input/30 dark:hover:bg-input/50 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40',
			// Without a page color-scheme, option popups would keep light Canvas under dark text.
			'[&_option]:bg-popover [&_option]:text-popover-foreground',
			multiple && 'h-auto pr-2.5 data-[size=sm]:h-auto'
		)}
		{...restProps}
	>
		{@render children?.()}
	</select>
	{#if !multiple}
		<ChevronDownIcon
			class="pointer-events-none absolute top-1/2 right-2.5 size-4 -translate-y-1/2 text-muted-foreground select-none"
			aria-hidden="true"
			data-slot="native-select-icon"
		/>
	{/if}
</span>
