<script lang="ts">
	import { displayLabel } from '$lib/labels';
	import { mode } from 'mode-watcher';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import * as Tabs from '$lib/components/ui/tabs';
	import type { RepoBlob } from '../types';
	import { parseRepositoryDocument } from './model';
	import { renderRepositoryMarkdown } from './render';
	import { diagrams } from './diagrams';
	let {
		blob,
		fragment = '',
		onopen,
		onreference,
		ondirectory,
		onback
	}: {
		blob: RepoBlob;
		fragment?: string;
		onopen: (path: string, fragment?: string) => void;
		onreference: (id: string) => void;
		ondirectory: (path: string) => void;
		onback?: () => void;
	} = $props();
	let tab = $state('preview');
	let article = $state<HTMLElement>();
	const parsed = $derived.by(() => {
		if (blob.encoding !== 'utf-8' || !blob.path.toLowerCase().endsWith('.md')) return null;
		try {
			return { document: parseRepositoryDocument(blob), error: '' };
		} catch (error) {
			return { document: null, error: String(error) };
		}
	});
	const rendered = $derived(parsed?.document ? renderRepositoryMarkdown(parsed.document) : null);
	function scrollTo(fragment: string) {
		const heading = [...(article?.querySelectorAll<HTMLElement>('[id]') || [])].find(
			(node) => node.id === fragment
		);
		heading?.scrollIntoView?.({ block: 'start' });
		heading?.focus();
	}
	$effect(() => {
		if (rendered && fragment && article) scrollTo(fragment);
	});
	function follow(event: MouseEvent) {
		const link = (event.target as Element).closest<HTMLAnchorElement>('a');
		if (!link || !article?.contains(link)) return;
		if (link.dataset.documentId) {
			event.preventDefault();
			onreference(link.dataset.documentId);
		} else if (link.dataset.repositoryPath !== undefined) {
			event.preventDefault();
			if (link.dataset.repositoryDirectory === 'true') ondirectory(link.dataset.repositoryPath);
			else if (link.dataset.repositoryPath === blob.path) scrollTo(link.dataset.fragment || '');
			else onopen(link.dataset.repositoryPath, link.dataset.fragment || '');
		}
	}
	function links(node: HTMLElement) {
		node.addEventListener('click', follow);
		return { destroy: () => node.removeEventListener('click', follow) };
	}
</script>

<section aria-label="Document preview" class="min-w-0 space-y-4">
	<div class="flex flex-wrap items-start justify-between gap-3">
		<div class="min-w-0 space-y-1">
			<h3 class="text-base font-semibold">
				{parsed?.document?.title || blob.path.split('/').at(-1)}
			</h3>
			<p class="font-mono text-xs break-all text-muted-foreground">{blob.path}</p>
			{#if parsed?.document?.id}<Badge variant="outline">{parsed.document.id}</Badge>{/if}
			{#if parsed?.document?.status}<Badge variant="secondary"
					>{displayLabel(parsed.document.status)}</Badge
				>{/if}
		</div>
		{#if onback}<Button variant="ghost" size="sm" onclick={onback}>Back to files</Button>{/if}
	</div>
	{#if blob.encoding !== 'utf-8'}
		<p class="text-sm text-muted-foreground">
			Binary file cannot be displayed inline ({blob.size} bytes).
		</p>
	{:else}
		<Tabs.Root bind:value={tab}>
			<Tabs.List aria-label="Document representation"
				><Tabs.Trigger value="preview">Preview</Tabs.Trigger><Tabs.Trigger value="source"
					>Source</Tabs.Trigger
				></Tabs.List
			>
			<Tabs.Content value="preview" class="space-y-4">
				{#if parsed?.error}<p role="alert" class="text-sm text-destructive">
						{parsed.error} Select Source to inspect the file.
					</p>{/if}
				{#if parsed?.document}
					{#if Object.keys(parsed.document.meta).length}
						<details class="rounded-lg border p-3 text-sm">
							<summary class="cursor-pointer font-medium">Document metadata</summary>
							<dl class="mt-3 space-y-2">
								{#each Object.entries(parsed.document.meta) as [key, value] (key)}<div
										class="space-y-1"
									>
										<dt class="font-medium">{key}</dt>
										<dd class="font-mono text-xs break-words text-muted-foreground">
											{typeof value === 'string' ? value : JSON.stringify(value)}
										</dd>
									</div>{/each}
							</dl>
						</details>
					{/if}
				{/if}
				{#if rendered}
					{#if rendered.headings.length > 1}<nav
							aria-label="Document headings"
							class="flex flex-wrap gap-2"
						>
							{#each rendered.headings as heading (heading.id)}<Button
									variant="link"
									size="sm"
									onclick={() => scrollTo(heading.id)}>{heading.title}</Button
								>{/each}
						</nav>{/if}
					<!-- Sanitized anchors keep keyboard activation through delegated link handling. -->
					{#key `${rendered.html}-${mode.current}`}
						<article
							bind:this={article}
							use:links
							class="prose prose-sm max-w-none break-words dark:prose-invert"
							use:diagrams={{ html: rendered.html, dark: mode.current === 'dark' }}
						>
							<!-- renderRepositoryMarkdown sanitizes HTML with DOMPurify before adding controlled links. -->
							<!-- eslint-disable-next-line svelte/no-at-html-tags -->
							{@html rendered.html}
						</article>
					{/key}
				{:else if !parsed?.error}<pre
						class="overflow-auto rounded-lg bg-muted p-4 text-xs whitespace-pre-wrap">{blob.content}</pre>{/if}
			</Tabs.Content>
			<Tabs.Content value="source"
				><pre
					class="overflow-auto rounded-lg bg-muted p-4 text-xs whitespace-pre-wrap">{blob.content}</pre></Tabs.Content
			>
		</Tabs.Root>
	{/if}
</section>
