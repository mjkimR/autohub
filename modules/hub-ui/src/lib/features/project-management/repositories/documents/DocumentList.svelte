<script lang="ts">
	import WrapAtSeparators from '../../pipeline-runs/WrapAtSeparators.svelte';
	import { displayLabel } from '$lib/labels';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import type { RepositoryDocument } from './model';
	let {
		documents,
		query = $bindable(''),
		selectedPath = '',
		loading = false,
		onopen
	}: {
		documents: RepositoryDocument[];
		query?: string;
		selectedPath?: string;
		loading?: boolean;
		onopen: (path: string) => void;
	} = $props();
	const filtered = $derived(
		documents.filter((doc) =>
			`${doc.title} ${doc.id} ${doc.status} ${doc.path}`.toLowerCase().includes(query.toLowerCase())
		)
	);
</script>

<div class="min-w-0 space-y-3">
	<label class="block space-y-1 text-sm"
		><span class="font-medium">Find documents</span><Input
			bind:value={query}
			placeholder="Title, ID, status or path"
		/></label
	>
	<p class="text-xs text-muted-foreground">{filtered.length} of {documents.length} documents</p>
	{#if !documents.length && !loading}<p class="text-sm text-muted-foreground">
			No documents in this section on the selected branch.
		</p>
	{:else if !filtered.length && !loading}<p class="text-sm text-muted-foreground">
			No matching documents.
		</p>
		<Button variant="outline" size="sm" onclick={() => (query = '')}>Clear search</Button>
	{:else}
		<ul class="max-h-72 space-y-3 overflow-auto lg:max-h-128" aria-label="Repository documents">
			{#each filtered as doc (doc.path)}<li class="space-y-1 border-b pb-3">
					<Button
						variant={selectedPath === doc.path ? 'secondary' : 'ghost'}
						size="sm"
						class="max-w-full justify-start"
						onclick={() => onopen(doc.path)}
						aria-current={selectedPath === doc.path ? 'page' : undefined}
						><span class="truncate" title={doc.title}>{doc.title}</span></Button
					>
					<div class="flex flex-wrap items-center gap-2">
						{#if doc.id}<span class="text-xs text-muted-foreground">{doc.id}</span
							>{/if}{#if doc.status}<Badge variant="outline">{displayLabel(doc.status)}</Badge>{/if}
					</div>
					<p class="font-mono text-xs break-words text-muted-foreground">
						<WrapAtSeparators text={doc.path} />
					</p>
				</li>{/each}
		</ul>
	{/if}
</div>
