<script lang="ts">
	import { Folder, FileText, CornerLeftUp } from '@lucide/svelte';
	import type { RepoItem } from './types';

	let {
		items,
		currentPath = '',
		onnavigate,
		onselect
	}: {
		items: RepoItem[];
		currentPath?: string;
		onnavigate: (path: string) => void;
		onselect: (item: RepoItem) => void;
	} = $props();

	function formatBytes(bytes: number): string {
		if (bytes === 0) return '0 B';
		const k = 1024;
		const sizes = ['B', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
	}

	function goToParent() {
		const parts = currentPath.split('/').filter(Boolean);
		parts.pop();
		onnavigate(parts.join('/'));
	}
</script>

<div class="overflow-hidden rounded-xl border bg-card shadow-xs">
	<div class="border-b bg-muted/40 px-4 py-2.5 text-xs font-semibold text-muted-foreground">
		<div class="grid grid-cols-12 gap-2">
			<div class="col-span-8 sm:col-span-9">Name</div>
			<div class="col-span-4 text-right sm:col-span-3">Size</div>
		</div>
	</div>

	<div class="divide-y divide-border/60 text-sm">
		{#if currentPath}
			<button
				type="button"
				onclick={goToParent}
				class="flex w-full items-center gap-3 px-4 py-2.5 text-left text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground"
			>
				<CornerLeftUp class="h-4 w-4 shrink-0 text-muted-foreground" />
				<span class="font-medium">..</span>
			</button>
		{/if}

		{#if items.length === 0}
			<div class="px-4 py-8 text-center text-sm text-muted-foreground">Empty directory</div>
		{:else}
			{#each items as item (item.path)}
				<div
					class="grid grid-cols-12 items-center gap-2 px-4 py-2.5 transition-colors hover:bg-muted/40"
				>
					<button
						type="button"
						onclick={() => (item.type === 'dir' ? onnavigate(item.path) : onselect(item))}
						class="col-span-8 flex items-center gap-3 truncate text-left sm:col-span-9"
					>
						{#if item.type === 'dir'}
							<Folder class="h-4 w-4 shrink-0 text-amber-500/90 dark:text-amber-400" />
							<span class="truncate font-medium text-foreground hover:underline">
								{item.name}
							</span>
						{:else}
							<FileText class="h-4 w-4 shrink-0 text-muted-foreground" />
							<span class="truncate text-foreground/90 hover:underline">
								{item.name}
							</span>
						{/if}
					</button>

					<div class="col-span-4 text-right font-mono text-xs text-muted-foreground sm:col-span-3">
						{#if item.type === 'dir'}
							—
						{:else}
							{formatBytes(item.size)}
						{/if}
					</div>
				</div>
			{/each}
		{/if}
	</div>
</div>
