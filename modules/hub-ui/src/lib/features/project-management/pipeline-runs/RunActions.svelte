<script lang="ts">
	import type { components } from '$lib/api';
	import { Button } from '$lib/components/ui/button';
	import * as DropdownMenu from '$lib/components/ui/dropdown-menu';
	import {
		ChevronsRight,
		Ellipsis,
		ExternalLink,
		History,
		Link2,
		MessageSquare,
		Pause,
		Play,
		XCircle
	} from '@lucide/svelte';
	import { canResume, isTerminalRun, primaryRunAction, type RunDecisions } from './run-actions';
	import type { RunSection } from './run-links';

	type Run = components['schemas']['PipelineRunRead'];
	let {
		run,
		decisions,
		operating = false,
		layout = 'row',
		href,
		onadvance,
		onpause,
		onresume,
		oncancel,
		onattach
	}: {
		run: Run;
		decisions: RunDecisions;
		operating?: boolean;
		/** `row` shows one primary plus an overflow menu; `page` shows its secondaries inline. */
		layout?: 'row' | 'page';
		/** URL of a run page section (the page itself without a section). */
		href: (section?: RunSection) => string;
		onadvance: () => void;
		onpause: () => void;
		onresume: () => void;
		oncancel: () => void;
		onattach: () => void;
	} = $props();

	let primary = $derived(primaryRunAction(run, decisions));
	let terminal = $derived(isTerminalRun(run));
	let stopped = $derived(run.state === 'paused' || run.state === 'blocked');
	let showResume = $derived(primary.kind !== 'resume' && canResume(run, decisions));
	let showPause = $derived(!terminal && !stopped);
	let showAttach = $derived(!terminal && !run.pull_number && primary.kind !== 'attach-pr');
	let rowLabel = $derived(`PR #${run.pull_number || 'pending'}`);
</script>

{#snippet primaryButton()}
	{@const size = layout === 'page' ? 'default' : 'sm'}
	{@const text = layout === 'page' ? primary.label : primary.short}
	{@const name = text === primary.label ? undefined : primary.label}
	{#if primary.kind === 'resume'}
		<Button {size} disabled={operating} onclick={onresume}>
			<Play aria-hidden="true" />{text}
		</Button>
	{:else if primary.kind === 'attach-pr'}
		<Button {size} disabled={operating} onclick={onattach}>
			<Link2 aria-hidden="true" />{text}
		</Button>
	{:else if !(layout === 'page' && (primary.kind === 'open' || primary.kind === 'next-step'))}
		<!-- On the page the next-step section itself is the primary region, so no jump link is needed. -->
		<Button
			{size}
			variant={primary.kind === 'open' ? 'outline' : 'default'}
			href={href(primary.section)}
			aria-label={name}
		>
			{#if primary.section === 'decisions'}<MessageSquare aria-hidden="true" />{/if}
			{text}
		</Button>
	{/if}
{/snippet}

{#if layout === 'page'}
	<div class="flex flex-wrap items-center gap-2">
		{@render primaryButton()}
		{#if showResume}
			<Button variant="outline" disabled={operating} onclick={onresume}
				><Play aria-hidden="true" />Resume</Button
			>
		{/if}
		{#if showPause}
			<Button variant="outline" disabled={operating} onclick={onpause}
				><Pause aria-hidden="true" />Pause</Button
			>
		{/if}
		{#if !terminal}
			<Button
				variant="outline"
				disabled={operating}
				onclick={onadvance}
				title="Re-evaluate this run now instead of waiting for its next scheduled check"
				><ChevronsRight aria-hidden="true" />Advance now</Button
			>
		{/if}
		{#if showAttach}
			<Button variant="outline" disabled={operating} onclick={onattach}
				><Link2 aria-hidden="true" />Attach PR</Button
			>
		{/if}
		{#if run.pull_url}
			<Button variant="ghost" href={run.pull_url} target="_blank" rel="noreferrer"
				><ExternalLink aria-hidden="true" />Inspect PR</Button
			>
		{/if}
		{#if !terminal}
			<Button variant="subtle-destructive" disabled={operating} onclick={oncancel}
				><XCircle aria-hidden="true" />Cancel run</Button
			>
		{/if}
	</div>
{:else}
	<div class="flex items-center gap-1 md:justify-end">
		{@render primaryButton()}
		<DropdownMenu.Root>
			<DropdownMenu.Trigger>
				{#snippet child({ props })}
					<Button
						{...props}
						variant="subtle"
						size="icon-sm"
						disabled={operating}
						aria-label={`More actions for ${rowLabel}`}
						title="More actions"><Ellipsis aria-hidden="true" /></Button
					>
				{/snippet}
			</DropdownMenu.Trigger>
			<DropdownMenu.Content align="end" class="w-56">
				{#if primary.kind !== 'open'}
					<DropdownMenu.Item>
						{#snippet child({ props })}<a {...props} href={href()}>Open run</a>{/snippet}
					</DropdownMenu.Item>
				{/if}
				<DropdownMenu.Item>
					{#snippet child({ props })}<a {...props} href={href('decisions')}
							><MessageSquare aria-hidden="true" />Decisions</a
						>{/snippet}
				</DropdownMenu.Item>
				<DropdownMenu.Item>
					{#snippet child({ props })}<a {...props} href={href('attempts')}
							><History aria-hidden="true" />Attempts &amp; errors</a
						>{/snippet}
				</DropdownMenu.Item>
				{#if showResume || showPause || !terminal || showAttach}
					<DropdownMenu.Separator />
				{/if}
				{#if showResume}
					<DropdownMenu.Item onSelect={onresume}
						><Play aria-hidden="true" />Resume</DropdownMenu.Item
					>
				{/if}
				{#if showPause}
					<DropdownMenu.Item onSelect={onpause}><Pause aria-hidden="true" />Pause</DropdownMenu.Item
					>
				{/if}
				{#if !terminal}
					<DropdownMenu.Item onSelect={onadvance}
						><ChevronsRight aria-hidden="true" />Advance now</DropdownMenu.Item
					>
				{/if}
				{#if showAttach}
					<DropdownMenu.Item onSelect={onattach}
						><Link2 aria-hidden="true" />Attach PR</DropdownMenu.Item
					>
				{/if}
				{#if run.pull_url}
					<DropdownMenu.Item>
						{#snippet child({ props })}<a
								{...props}
								href={run.pull_url}
								target="_blank"
								rel="noreferrer"><ExternalLink aria-hidden="true" />Inspect PR</a
							>{/snippet}
					</DropdownMenu.Item>
				{/if}
				{#if !terminal}
					<DropdownMenu.Separator />
					<DropdownMenu.Item variant="destructive" onSelect={oncancel}
						><XCircle aria-hidden="true" />Cancel run</DropdownMenu.Item
					>
				{/if}
			</DropdownMenu.Content>
		</DropdownMenu.Root>
	</div>
{/if}
