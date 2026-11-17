<script lang="ts">
	import WrapAtSeparators from '../../pipeline-runs/WrapAtSeparators.svelte';
	import { displayLabel } from '$lib/labels';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { milestoneRows } from './discovery';
	import type { RepositoryDocument } from './model';
	let { documents, onopen }: { documents: RepositoryDocument[]; onopen: (path: string) => void } =
		$props();
	const rows = $derived(milestoneRows(documents));
</script>

<div class="space-y-4">
	<p class="text-xs text-muted-foreground">
		Dependencies describe repository documents. They do not authorize or start work.
	</p>
	{#if !rows.length}<p class="text-sm text-muted-foreground">
			No milestones on the selected branch.
		</p>{/if}
	{#each rows as row (row.document.path)}
		<section class="space-y-3 rounded-lg border p-4" aria-label={row.document.title}>
			<div class="flex flex-wrap items-center gap-2">
				<Button variant="link" onclick={() => onopen(row.document.path)}
					>{row.document.title}</Button
				><Badge variant="outline">{displayLabel(row.document.status || 'unknown')}</Badge>
			</div>
			<p class="font-mono text-xs break-words text-muted-foreground">
				<WrapAtSeparators text={row.document.path} />
			</p>
			{#if row.dependencies.length}<p class="text-sm">
					Depends on: {row.dependencies
						.map((dependency) => `${dependency.id} (${dependency.status})`)
						.join(', ')}
				</p>{/if}
			{#if row.members.length}<ul class="space-y-2" aria-label="Direct proposal members">
					{#each row.members as member (member.path)}<li>
							<Button variant="outline" size="sm" onclick={() => onopen(member.path)}
								>{member.title}</Button
							><span class="ml-2 text-xs text-muted-foreground">{displayLabel(member.status)}</span>
						</li>{/each}
				</ul>
			{:else}<p class="text-sm text-muted-foreground">No direct proposal members.</p>{/if}
		</section>
	{/each}
</div>
