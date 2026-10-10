<script lang="ts">
	import type { components } from '$lib/api/schema';
	import { Button } from '$lib/components/ui/button';
	import { Tabs, TabsContent, TabsList, TabsTrigger } from '$lib/components/ui/tabs';
	import { toast } from 'svelte-sonner';

	type Issued = components['schemas']['KeyIssued'];
	let { issued, scopes, ondismiss }: { issued: Issued; scopes: string[]; ondismiss: () => void } =
		$props();

	let scope = $state('project');

	const connections = $derived([
		...(scopes.some((scope) => ['autohub:mcp:read', 'autohub:mcp:write'].includes(scope))
			? [{ name: 'autohub', path: '/mcp/', env: 'AUTOHUB_MCP_KEY', label: 'Work MCP' }]
			: []),
		...(scopes.includes('autohub:mcp:ops')
			? [
					{
						name: 'autohub-ops',
						path: '/ops/mcp/',
						env: 'AUTOHUB_OPS_MCP_KEY',
						label: 'Operations MCP'
					}
				]
			: [])
	]);

	async function copy(text: string, what: string) {
		try {
			await navigator.clipboard.writeText(text);
			toast.success(`${what} copied`);
		} catch {
			toast.error('Could not copy. Select the text and copy it manually.');
		}
	}
</script>

<section class="space-y-4 rounded-lg border border-primary p-4" aria-label="Issued key">
	<h3 class="font-semibold">Key issued: {issued.label}</h3>
	<p class="text-sm text-muted-foreground">
		This key is shown only once. Store it now; it cannot be retrieved later.
	</p>
	<div class="flex items-center gap-2">
		<code class="min-w-0 flex-1 rounded bg-muted p-2 text-xs break-all" data-testid="issued-key"
			>{issued.key}</code
		>
		<Button size="sm" variant="outline" onclick={() => copy(issued.key, 'Key')}>Copy key</Button>
	</div>
	{#each connections as connection (connection.name)}
		{@const endpoint = `${window.location.origin}${connection.path}`}
		{@const antigravityConfig = JSON.stringify(
			{
				mcpServers: {
					[connection.name]: {
						serverUrl: endpoint,
						headers: {
							Authorization: `Bearer ${issued.key}`
						}
					}
				}
			},
			null,
			2
		)}
		{@const claudeProjectCommand = `claude mcp add --transport http ${connection.name} ${endpoint} --header "Authorization: Bearer ${issued.key}"`}
		{@const claudeGlobalCommand = `claude mcp add --transport http --scope user ${connection.name} ${endpoint} --header "Authorization: Bearer ${issued.key}"`}
		{@const codexConfig = `[mcp_servers.${connection.name}]\nurl = "${endpoint}"\nbearer_token_env_var = "${connection.env}"`}
		<div class="space-y-3">
			<p class="text-sm font-semibold">{connection.label}</p>
			<Tabs bind:value={scope} class="w-full">
				<TabsList class="grid w-full grid-cols-2">
					<TabsTrigger value="project">Project level</TabsTrigger>
					<TabsTrigger value="global">Global</TabsTrigger>
				</TabsList>
				{#if scope === 'project'}
					<TabsContent value="project" class="space-y-3 pt-2">
						<div class="space-y-1">
							<p class="text-sm font-medium">Antigravity (.agents/mcp_config.json)</p>
							<div class="flex items-start gap-2">
								<pre
									class="min-w-0 flex-1 overflow-x-auto rounded bg-muted p-2 text-xs">{antigravityConfig}</pre>
								<Button
									size="sm"
									variant="outline"
									onclick={() => copy(antigravityConfig, 'Config')}>Copy</Button
								>
							</div>
						</div>
						<div class="space-y-1">
							<p class="text-sm font-medium">Claude Code (run in project directory)</p>
							<div class="flex items-start gap-2">
								<code class="min-w-0 flex-1 rounded bg-muted p-2 text-xs break-all"
									>{claudeProjectCommand}</code
								>
								<Button
									size="sm"
									variant="outline"
									onclick={() => copy(claudeProjectCommand, 'Command')}>Copy</Button
								>
							</div>
						</div>
						<div class="space-y-1">
							<p class="text-sm font-medium">
								Codex (.codex/config.toml, key in {connection.env})
							</p>
							<div class="flex items-start gap-2">
								<pre
									class="min-w-0 flex-1 overflow-x-auto rounded bg-muted p-2 text-xs">{codexConfig}</pre>
								<Button size="sm" variant="outline" onclick={() => copy(codexConfig, 'Config')}
									>Copy</Button
								>
							</div>
						</div>
					</TabsContent>
				{:else}
					<TabsContent value="global" class="space-y-3 pt-2">
						<div class="space-y-1">
							<p class="text-sm font-medium">Antigravity (~/.gemini/config/mcp_config.json)</p>
							<div class="flex items-start gap-2">
								<pre
									class="min-w-0 flex-1 overflow-x-auto rounded bg-muted p-2 text-xs">{antigravityConfig}</pre>
								<Button
									size="sm"
									variant="outline"
									onclick={() => copy(antigravityConfig, 'Config')}>Copy</Button
								>
							</div>
						</div>
						<div class="space-y-1">
							<p class="text-sm font-medium">Claude Code (global user scope)</p>
							<div class="flex items-start gap-2">
								<code class="min-w-0 flex-1 rounded bg-muted p-2 text-xs break-all"
									>{claudeGlobalCommand}</code
								>
								<Button
									size="sm"
									variant="outline"
									onclick={() => copy(claudeGlobalCommand, 'Command')}>Copy</Button
								>
							</div>
						</div>
						<div class="space-y-1">
							<p class="text-sm font-medium">
								Codex (~/.codex/config.toml, key in {connection.env})
							</p>
							<div class="flex items-start gap-2">
								<pre
									class="min-w-0 flex-1 overflow-x-auto rounded bg-muted p-2 text-xs">{codexConfig}</pre>
								<Button size="sm" variant="outline" onclick={() => copy(codexConfig, 'Config')}
									>Copy</Button
								>
							</div>
						</div>
					</TabsContent>
				{/if}
			</Tabs>
		</div>
	{/each}
	<Button size="sm" onclick={ondismiss}>I stored the key</Button>
</section>
