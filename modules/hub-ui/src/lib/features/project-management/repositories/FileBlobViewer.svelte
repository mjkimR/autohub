<script lang="ts">
	import { Copy, Check, Code, Eye, FileText } from '@lucide/svelte';
	import { Button } from '$lib/components/ui/button';
	import { toast } from 'svelte-sonner';
	import type { RepoBlob } from './types';

	let { blob, onback }: { blob: RepoBlob; onback?: () => void } = $props();

	let copied = $state(false);
	let viewTab = $state<'preview' | 'source'>('preview');

	let isMarkdown = $derived(blob.path.toLowerCase().endsWith('.md'));
	let lines = $derived(blob.content.split('\n'));

	async function copyContent() {
		try {
			await navigator.clipboard.writeText(blob.content);
			copied = true;
			toast.success('Copied to clipboard');
			setTimeout(() => {
				copied = false;
			}, 2000);
		} catch {
			toast.error('Failed to copy');
		}
	}

	function formatBytes(bytes: number): string {
		if (bytes === 0) return '0 B';
		const k = 1024;
		const sizes = ['B', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
	}
</script>

<div class="overflow-hidden rounded-xl border bg-card shadow-xs">
	<!-- File Header -->
	<div class="flex flex-wrap items-center justify-between gap-3 border-b bg-muted/40 px-4 py-3">
		<div class="flex items-center gap-2">
			{#if onback}
				<button
					type="button"
					onclick={onback}
					class="text-xs font-medium text-muted-foreground hover:text-foreground hover:underline"
				>
					← Back
				</button>
				<span class="text-muted-foreground/60">/</span>
			{/if}
			<FileText class="h-4 w-4 text-muted-foreground" />
			<span class="font-mono text-sm font-semibold text-foreground">{blob.path}</span>
			<span class="rounded bg-muted px-2 py-0.5 font-mono text-xs text-muted-foreground">
				{formatBytes(blob.size)}
			</span>
		</div>

		<div class="flex items-center gap-2">
			{#if isMarkdown}
				<div class="flex rounded-lg border bg-background p-0.5 text-xs">
					<button
						type="button"
						onclick={() => (viewTab = 'preview')}
						class={`flex items-center gap-1.5 rounded-md px-2.5 py-1 font-medium transition-colors ${viewTab === 'preview' ? 'bg-primary text-primary-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground'}`}
					>
						<Eye class="h-3.5 w-3.5" />
						Preview
					</button>
					<button
						type="button"
						onclick={() => (viewTab = 'source')}
						class={`flex items-center gap-1.5 rounded-md px-2.5 py-1 font-medium transition-colors ${viewTab === 'source' ? 'bg-primary text-primary-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground'}`}
					>
						<Code class="h-3.5 w-3.5" />
						Source
					</button>
				</div>
			{/if}

			<Button variant="outline" size="sm" class="h-8 gap-1.5 text-xs" onclick={copyContent}>
				{#if copied}
					<Check class="h-3.5 w-3.5 text-emerald-500" />
					Copied
				{:else}
					<Copy class="h-3.5 w-3.5" />
					Copy
				{/if}
			</Button>
		</div>
	</div>

	<!-- File Content -->
	{#if blob.encoding === 'base64'}
		<div class="p-8 text-center text-sm text-muted-foreground">
			Binary file cannot be displayed inline ({formatBytes(blob.size)})
		</div>
	{:else if isMarkdown && viewTab === 'preview'}
		<div class="prose prose-sm max-w-none p-6 md:p-8 dark:prose-invert">
			<!-- Render formatted markdown or simple whitespace preserved text -->
			<div class="font-sans leading-relaxed whitespace-pre-wrap text-foreground">
				{blob.content}
			</div>
		</div>
	{:else}
		<div class="max-h-[700px] overflow-auto bg-muted/10 font-mono text-xs">
			<table class="w-full border-collapse">
				<tbody>
					{#each lines as line, idx (idx)}
						<tr class="transition-colors hover:bg-muted/50">
							<td
								class="w-12 border-r border-border/40 py-0.5 pr-3 text-right text-muted-foreground/50 select-none"
							>
								{idx + 1}
							</td>
							<td class="py-0.5 pl-4 whitespace-pre-wrap text-foreground/90">
								{line || ' '}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>
