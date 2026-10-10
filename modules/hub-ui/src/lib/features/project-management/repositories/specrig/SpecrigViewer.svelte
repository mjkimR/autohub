<script lang="ts">
	import KnowledgeViews from './KnowledgeViews.svelte';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	import { parseDocument } from 'yaml';

	import {
		httpDataSource,
		normalizeTree,
		type TreeItem,
		type RepositoryDataSource,
		type RepositoryInfo
	} from './repository';

	interface Frontmatter {
		id?: string;
		title?: string;
		status?: string;
		target_area?: string;
		milestone?: string;
		priority?: string;
		size?: string;
		[key: string]: any;
	}

	let {
		repoId = '',
		apiBase = '',
		branch = 'main',
		initialPath = 'docs/',
		initialView = 'files',
		initialAnchor = '',
		theme = 'dark',
		dataSource = undefined
	} = $props<{
		repoId?: string;
		apiBase?: string;
		branch?: string;
		initialPath?: string;
		initialView?: string;
		initialAnchor?: string;
		theme?: string;
		dataSource?: RepositoryDataSource;
	}>();

	let currentTheme = $state<'dark' | 'light'>('dark');

	$effect(() => {
		if (theme === 'light' || theme === 'dark') {
			currentTheme = theme;
		} else if (typeof localStorage !== 'undefined') {
			const saved = localStorage.getItem('specrig-theme');
			if (saved === 'light' || saved === 'dark') {
				currentTheme = saved;
			}
		}
	});

	$effect(() => {
		if (hostEl) {
			hostEl.setAttribute('data-theme', currentTheme);
		}
	});

	function toggleTheme() {
		currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
		try {
			localStorage?.setItem('specrig-theme', currentTheme);
		} catch {}
	}

	let view = $state<'files' | 'book' | 'proposals' | 'specs'>('files');
	let currentPath = $state('docs/');
	$effect(() => {
		view = ['book', 'proposals', 'specs'].includes(initialView)
			? (initialView as typeof view)
			: 'files';
	});
	let treeItems = $state<TreeItem[]>([]);
	let currentBlob = $state<{
		path: string;
		content: string;
		frontmatter: Frontmatter | null;
		html: string;
	} | null>(null);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let searchQuery = $state('');
	let rawMode = $state(false);
	let hostEl: HTMLElement | null = null;
	let generation = 0;
	let repoInfo = $state<RepositoryInfo | null>(null);
	let fullscreenSvg = $state<string | null>(null);
	let zoomLevel = $state(1);

	function openFullscreen(svg: string) {
		fullscreenSvg = svg;
		zoomLevel = 1;
	}

	function closeFullscreen() {
		fullscreenSvg = null;
	}

	function handleWheel(e: WheelEvent) {
		if (e.ctrlKey || e.metaKey) {
			e.preventDefault();
			const delta = e.deltaY < 0 ? 0.15 : -0.15;
			zoomLevel = Math.max(0.3, Math.min(4, +(zoomLevel + delta).toFixed(2)));
		}
	}

	$effect(() => {
		if (fullscreenSvg) {
			const handleKey = (e: KeyboardEvent) => {
				if (e.key === 'Escape') closeFullscreen();
			};
			window.addEventListener('keydown', handleKey);
			return () => window.removeEventListener('keydown', handleKey);
		}
	});
	const source = $derived(dataSource ?? (apiBase ? httpDataSource(apiBase) : null));

	$effect(() => {
		const repository = source;
		const controller = new AbortController();
		repoInfo = null;
		if (repository) {
			void repository
				.info(controller.signal)
				.then((info: any) => {
					if (!controller.signal.aborted) repoInfo = info;
				})
				.catch((err: any) => {
					if (!controller.signal.aborted) error = `저장소 정보 로드 실패: ${err?.message ?? err}`;
				});
		}
		return () => controller.abort();
	});

	$effect(() => {
		currentPath = initialPath;
	});

	// Only the current request may publish state or events.
	$effect(() => {
		const path = currentPath;
		const repository = source;
		const ref = branch;
		const id = ++generation;
		const controller = new AbortController();
		if (repository && view === 'files') {
			if (path.endsWith('/') || path === '') {
				void loadTree(path, repository, ref, id, controller.signal);
			} else {
				void loadBlob(path, repository, ref, id, controller.signal);
			}
		}
		return () => controller.abort();
	});

	function parseFrontmatterAndMarkdown(text: string): {
		frontmatter: Frontmatter | null;
		content: string;
	} {
		const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/);
		if (!match) return { frontmatter: null, content: text };
		const document = parseDocument(match[1]);
		if (document.errors.length) throw new Error(document.errors[0].message);
		const parsed = document.toJS({ maxAliasCount: 100 });
		return {
			frontmatter: parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : null,
			content: text.slice(match[0].length)
		};
	}

	async function loadTree(
		path: string,
		repository: RepositoryDataSource,
		ref: string,
		id: number,
		signal: AbortSignal
	) {
		loading = true;
		error = null;
		currentBlob = null;
		try {
			const cleanPath = path.replace(/\/+$/, '');
			const data = await repository.tree(cleanPath, ref, signal);
			if (id !== generation || signal.aborted) return;
			treeItems = normalizeTree(data);
			dispatchPathChange(path);
		} catch (err: any) {
			if (id !== generation || signal.aborted) return;
			error = `트리 로드 실패 (${path}): ${err.message}`;
		} finally {
			if (id === generation) loading = false;
		}
	}

	async function loadBlob(
		path: string,
		repository: RepositoryDataSource,
		ref: string,
		id: number,
		signal: AbortSignal
	) {
		loading = true;
		error = null;
		currentBlob = null;
		try {
			const data = await repository.blob(path, ref, signal);
			const parent = path.split('/').slice(0, -1).join('/');
			const siblings = await repository.tree(parent, ref, signal);
			if (id !== generation || signal.aborted) return;
			treeItems = normalizeTree(siblings);
			let rawContent: string;
			if (data.encoding === 'base64') {
				rawContent = new TextDecoder('utf-8', { fatal: true }).decode(
					Uint8Array.from(atob(data.content.replace(/\s/g, '')), (c) => c.charCodeAt(0))
				);
			} else if (data.encoding === 'utf-8') {
				rawContent = data.content;
			} else {
				throw new Error(`Unsupported encoding: ${data.encoding}`);
			}
			const { frontmatter, content } = parseFrontmatterAndMarkdown(rawContent);
			const parsedHtml = DOMPurify.sanitize(
				marked.parse(content, { gfm: true, breaks: true }) as string,
				{ USE_PROFILES: { html: true } }
			);
			currentBlob = {
				path,
				content: rawContent,
				frontmatter,
				html: parsedHtml
			};
			dispatchPathChange(path);
			dispatchItemSelected(path, frontmatter);
		} catch (err: any) {
			if (id !== generation || signal.aborted) return;
			error = `파일 로드 실패 (${path}): ${err.message}`;
		} finally {
			if (id === generation) loading = false;
		}
	}

	function dispatchPathChange(path: string) {
		const event = new CustomEvent('specrig:path-change', {
			detail: { path, repoId, branch },
			bubbles: true,
			composed: true
		});
		hostEl?.dispatchEvent(event);
	}

	function dispatchItemSelected(path: string, frontmatter: Frontmatter | null) {
		const event = new CustomEvent('specrig:item-selected', {
			detail: { path, frontmatter, repoId, branch },
			bubbles: true,
			composed: true
		});
		hostEl?.dispatchEvent(event);
	}

	// Render into a detached host so Mermaid can use document-level SVG lookups.
	// Only sanitized SVG is inserted into the component's Shadow DOM.
	function renderDiagrams(node: HTMLElement) {
		const blob = currentBlob;
		let active = true;
		void (async () => {
			const diagrams = node.querySelectorAll<HTMLElement>('pre > code.language-mermaid');
			if (!diagrams.length) return;
			const { default: mermaid } = await import('mermaid');
			const isDark = currentTheme === 'dark';
			mermaid.initialize({
				startOnLoad: false,
				securityLevel: 'strict',
				htmlLabels: false,
				flowchart: { htmlLabels: false },
				theme: isDark ? 'dark' : 'default',
				themeVariables: isDark
					? {
							darkMode: true,
							background: '#111827',
							mainBkg: '#1e293b',
							primaryColor: '#1e293b',
							primaryTextColor: '#f8fafc',
							primaryBorderColor: '#475569',
							lineColor: '#94a3b8',
							textColor: '#e2e8f0',
							edgeLabelBackground: '#1e293b',
							tertiaryColor: '#0f172a',
							tertiaryTextColor: '#f8fafc',
							nodeBorder: '#475569',
							clusterBkg: '#0f172a',
							clusterBorder: '#334155'
						}
					: {
							darkMode: false,
							background: '#f8fafc',
							mainBkg: '#ffffff',
							primaryColor: '#ffffff',
							primaryTextColor: '#0f172a',
							primaryBorderColor: '#cbd5e1',
							lineColor: '#334155',
							textColor: '#1e293b',
							edgeLabelBackground: '#ffffff',
							nodeBorder: '#cbd5e1',
							clusterBkg: '#f1f5f9',
							clusterBorder: '#cbd5e1'
						}
			});
			for (const code of diagrams) {
				if (!active || blob !== currentBlob) return;
				const container = document.createElement('div');
				container.style.position = 'absolute';
				container.style.visibility = 'hidden';
				document.body.append(container);
				try {
					const { svg } = await mermaid.render(
						`specrig-${crypto.randomUUID()}`,
						code.textContent || '',
						container
					);
					if (active && blob === currentBlob) {
						const diagram = document.createElement('div');
						diagram.className = 'mermaid-diagram';

						const toolbar = document.createElement('div');
						toolbar.className = 'diagram-toolbar';

						const expandBtn = document.createElement('button');
						expandBtn.type = 'button';
						expandBtn.className = 'diagram-action-btn';
						expandBtn.title = '다이어그램 전체화면 보기 (Fullscreen)';
						expandBtn.innerHTML = `⛶ Fullscreen`;
						expandBtn.addEventListener('click', () => {
							openFullscreen(svg);
						});

						toolbar.appendChild(expandBtn);

						const svgWrap = document.createElement('div');
						svgWrap.className = 'diagram-svg-wrap';
						svgWrap.innerHTML = DOMPurify.sanitize(svg, {
							USE_PROFILES: { svg: true, svgFilters: true }
						});

						diagram.appendChild(toolbar);
						diagram.appendChild(svgWrap);
						code.parentElement?.replaceWith(diagram);
					}
				} catch (err) {
					if (active) code.parentElement?.setAttribute('title', `Mermaid: ${String(err)}`);
				} finally {
					container.remove();
				}
			}
		})().catch((err) => {
			if (active) error = `다이어그램 로드 실패: ${String(err)}`;
		});
		return {
			destroy() {
				active = false;
			}
		};
	}

	function navigateTo(path: string, isTree: boolean) {
		currentPath = isTree ? (path.endsWith('/') ? path : path + '/') : path;
	}

	function navigateParent() {
		const parts = currentPath.replace(/\/+$/, '').split('/');
		if (parts.length > 1) {
			parts.pop();
			currentPath = parts.join('/') + '/';
		} else {
			currentPath = '';
		}
	}

	const filteredItems = $derived(
		treeItems.filter(
			(item) => !searchQuery || item.name.toLowerCase().includes(searchQuery.toLowerCase())
		)
	);

	const breadcrumbs = $derived(currentPath ? currentPath.split('/').filter(Boolean) : []);
</script>

<div class="specrig-viewer-root" class:theme-light={currentTheme === 'light'} bind:this={hostEl}>
	<!-- Top Navigation Header -->
	<header class="viewer-header">
		<div class="brand-zone">
			<div class="logo-badge">
				<svg
					viewBox="0 0 24 24"
					width="16"
					height="16"
					stroke="currentColor"
					stroke-width="2"
					fill="none"
				>
					<polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
					<polyline points="2 17 12 22 22 17"></polyline>
					<polyline points="2 12 12 17 22 12"></polyline>
				</svg>
			</div>
			<span class="brand-title">Specrig Viewer</span>
			{#if repoId || repoInfo?.repo_id}
				<span class="repo-tag">{repoId || repoInfo?.repo_id}</span>
			{/if}
			<span class="branch-tag">🌿 {branch}</span>
		</div>

		<!-- Breadcrumbs -->
		<nav class="breadcrumb-bar" aria-label="Breadcrumb">
			<button class="crumb-btn" onclick={() => navigateTo('', true)}>root</button>
			{#each breadcrumbs as part, idx}
				<span class="crumb-sep">/</span>
				{#if idx === breadcrumbs.length - 1 && !currentPath.endsWith('/')}
					<span class="crumb-current">{part}</span>
				{:else}
					<button
						class="crumb-btn"
						onclick={() => navigateTo(breadcrumbs.slice(0, idx + 1).join('/') + '/', true)}
					>
						{part}
					</button>
				{/if}
			{/each}
		</nav>

		<div class="action-zone">
			{#if currentBlob && view === 'files'}
				<button class="mode-toggle-btn" class:active={rawMode} onclick={() => (rawMode = !rawMode)}>
					{rawMode ? '👁️ Preview' : '📝 Raw'}
				</button>
			{/if}
			<button
				class="theme-toggle-btn"
				title={currentTheme === 'dark' ? '라이트 모드로 전환' : '다크 모드로 전환'}
				onclick={toggleTheme}
			>
				{currentTheme === 'dark' ? '☀️ Light' : '🌙 Dark'}
			</button>
		</div>
	</header>

	<nav class="view-tabs" aria-label="탐색 방식">
		{#each [{ id: 'book', label: '문서 읽기' }, { id: 'proposals', label: 'Proposals' }, { id: 'specs', label: 'Specs' }, { id: 'files', label: '파일 탐색' }] as tab}
			<button
				aria-pressed={view === tab.id}
				class:active={view === tab.id}
				onclick={() => {
					view = tab.id as typeof view;
				}}>{tab.label}</button
			>
		{/each}
	</nav>
	{#if view !== 'files'}
		<div class="knowledge-host">
			<KnowledgeViews
				{view}
				{source}
				{branch}
				theme={currentTheme}
				requestedPath={initialPath}
				requestedAnchor={initialAnchor}
				diagrams={renderDiagrams}
				onOpen={(path) => {
					currentPath = path;
					view = 'files';
				}}
				onLocation={(path, anchor, selectedView, frontmatter) => {
					dispatchItemSelected(path, frontmatter);
					hostEl?.dispatchEvent(
						new CustomEvent('specrig:path-change', {
							detail: { path, anchor, view: selectedView, repoId, branch },
							bubbles: true,
							composed: true
						})
					);
				}}
			/>
		</div>
	{/if}
	<!-- Main Body Layout -->
	<div class="viewer-layout" class:hidden={view !== 'files'}>
		<!-- Left Sidebar: Explorer -->
		<aside class="sidebar-explorer">
			<div class="sidebar-header">
				<span class="section-label">EXPLORER</span>
				{#if currentPath}
					<button class="up-btn" title="Up one level" onclick={navigateParent}> ⬆ Up </button>
				{/if}
			</div>

			<div class="search-box">
				<input
					type="text"
					placeholder="Filter files..."
					bind:value={searchQuery}
					class="filter-input"
				/>
			</div>

			<div class="file-tree">
				{#if loading && !treeItems.length}
					<div class="loading-state">Loading directory...</div>
				{:else if filteredItems.length === 0}
					<div class="empty-state">No matching items</div>
				{:else}
					{#each filteredItems as item}
						<button
							class="tree-node"
							class:selected={currentPath === item.path ||
								(currentBlob && currentBlob.path === item.path)}
							onclick={() => navigateTo(item.path, item.type === 'tree')}
						>
							{#if item.type === 'tree'}
								<span class="node-icon folder">📁</span>
							{:else if item.name.endsWith('.md')}
								<span class="node-icon spec-file">📄</span>
							{:else}
								<span class="node-icon file">📑</span>
							{/if}
							<span class="node-name">{item.name}</span>
						</button>
					{/each}
				{/if}
			</div>
		</aside>

		<!-- Right Content Area -->
		<main class="content-viewport">
			{#if error}
				<div class="error-banner">
					<span class="error-icon">⚠️</span>
					<span>{error}</span>
				</div>
			{/if}

			{#if loading && !currentBlob}
				<div class="loading-placeholder">
					<div class="spinner"></div>
					<p>Fetching content...</p>
				</div>
			{:else if currentBlob}
				<!-- Document Header with Frontmatter Badges -->
				<div class="document-container">
					{#if currentBlob.frontmatter}
						<div class="frontmatter-panel">
							<div class="fm-header">
								{#if currentBlob.frontmatter.id}
									<span class="fm-id-badge">{currentBlob.frontmatter.id}</span>
								{/if}
								{#if currentBlob.frontmatter.status}
									<span class="fm-status-badge status-{currentBlob.frontmatter.status}">
										{currentBlob.frontmatter.status}
									</span>
								{/if}
								{#if currentBlob.frontmatter.priority}
									<span class="fm-badge priority-{currentBlob.frontmatter.priority}">
										{currentBlob.frontmatter.priority}
									</span>
								{/if}
								{#if currentBlob.frontmatter.milestone}
									<span class="fm-badge milestone">
										🎯 {currentBlob.frontmatter.milestone}
									</span>
								{/if}
								{#if currentBlob.frontmatter.target_area}
									<span class="fm-badge area">
										📂 {currentBlob.frontmatter.target_area}
									</span>
								{/if}
							</div>
							{#if currentBlob.frontmatter.title}
								<h1 class="document-title">{currentBlob.frontmatter.title}</h1>
							{/if}
						</div>
					{/if}

					<!-- Document Body -->
					{#if rawMode}
						<pre class="raw-content"><code>{currentBlob.content}</code></pre>
					{:else}
						{#key `${currentBlob.path}-${currentTheme}`}
							<article class="markdown-body" use:renderDiagrams>
								{@html currentBlob.html}
							</article>
						{/key}
					{/if}
				</div>
			{:else}
				<!-- Directory Overview Placeholder -->
				<div class="directory-placeholder">
					<div class="placeholder-icon">📚</div>
					<h2>Living Spec & Repository Explorer</h2>
					<p>
						Select a spec, blueprint, or document from the explorer on the left to start viewing.
					</p>
					<div class="quick-hints">
						<span class="hint-pill">Universal Git API</span>
						<span class="hint-pill">Shadow DOM Isolation</span>
						<span class="hint-pill">Svelte 5 Web Component</span>
					</div>
				</div>
			{/if}
		</main>
	</div>

	{#if fullscreenSvg}
		<div
			class="diagram-modal-backdrop"
			onclick={(e) => {
				if (e.target === e.currentTarget) closeFullscreen();
			}}
			onkeydown={(e) => {
				if (e.key === 'Escape') closeFullscreen();
			}}
			role="dialog"
			aria-modal="true"
			aria-label="Diagram Fullscreen View"
			tabindex="-1"
		>
			<div class="diagram-modal-window">
				<div class="modal-header">
					<div class="modal-title">
						<span>📊 Mermaid Diagram</span>
					</div>
					<div class="modal-controls">
						<button
							class="modal-btn"
							onclick={() => (zoomLevel = Math.max(0.3, +(zoomLevel - 0.2).toFixed(1)))}
							title="축소 (Ctrl + 휠 아래)">➖</button
						>
						<span class="zoom-indicator">{Math.round(zoomLevel * 100)}%</span>
						<button
							class="modal-btn"
							onclick={() => (zoomLevel = Math.min(4, +(zoomLevel + 0.2).toFixed(1)))}
							title="확대 (Ctrl + 휠 위)">➕</button
						>
						<button
							class="modal-btn reset-btn"
							onclick={() => (zoomLevel = 1)}
							title="기본 크기 (100%)">Reset</button
						>
						<button class="modal-btn close-btn" onclick={closeFullscreen} title="닫기 (ESC)"
							>✕ Close</button
						>
					</div>
				</div>
				<div class="modal-content" onwheel={handleWheel}>
					<div class="modal-svg-canvas" style="transform: scale({zoomLevel});">
						{@html DOMPurify.sanitize(fullscreenSvg, {
							USE_PROFILES: { svg: true, svgFilters: true }
						})}
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	.view-tabs {
		display: flex;
		gap: 8px;
		padding: 10px 16px;
		border-bottom: 1px solid var(--border-panel);
		background: var(--bg-header);
	}
	.view-tabs button {
		font: inherit;
		cursor: pointer;
		padding: 8px 14px;
		border: 0;
		border-radius: 6px;
		background: transparent;
		color: var(--text-secondary);
	}
	.view-tabs button.active {
		background: var(--tree-selected-bg);
		color: var(--tree-selected-text);
	}
	.view-tabs button:focus-visible {
		outline: 2px solid var(--tree-selected-text);
	}
	.knowledge-host {
		flex: 1;
		min-height: 0;
		overflow: hidden;
	}
	.viewer-layout.hidden {
		display: none;
	}

	:host {
		display: block;
		width: 100%;
		height: 100%;
		font-family:
			-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
		color: #e2e8f0;
		background-color: #0b0f17;
		box-sizing: border-box;
		overflow: hidden;
	}

	:host([data-theme='light']) {
		color: #334155;
		background-color: #ffffff;
	}

	*,
	*::before,
	*::after {
		box-sizing: border-box;
	}

	.specrig-viewer-root {
		--bg-header: #1e293b;
		--border-header: #334155;
		--bg-sidebar: #111827;
		--border-sidebar: #1f2937;
		--bg-viewport: #0b0f17;
		--bg-panel: #111827;
		--border-panel: #1f2937;
		--text-primary: #f8fafc;
		--text-secondary: #d1d5db;
		--text-muted: #94a3b8;
		--text-dim: #6b7280;
		--bg-input: #1f2937;
		--border-input: #374151;
		--bg-btn: #334155;
		--border-btn: #475569;
		--text-btn: #e2e8f0;
		--btn-hover-bg: #475569;
		--tree-hover-bg: #1f2937;
		--tree-selected-bg: #1e1b4b;
		--tree-selected-text: #818cf8;
		--code-bg: #1e293b;
		--code-color: #38bdf8;
		--pre-bg: #111827;
		--pre-border: #1f2937;
		--pre-text: #e5e7eb;
		--table-border: #374151;
		--th-bg: #1f2937;
		--th-text: #f9fafb;
		--badge-bg: #1f2937;
		--badge-text: #9ca3af;
		--branch-bg: #334155;
		--branch-text: #94a3b8;

		display: flex;
		flex-direction: column;
		height: 100%;
		width: 100%;
		background-color: var(--bg-viewport);
		color: var(--text-secondary);
	}

	.specrig-viewer-root.theme-light {
		--bg-header: #ffffff;
		--border-header: #e2e8f0;
		--bg-sidebar: #f8fafc;
		--border-sidebar: #e2e8f0;
		--bg-viewport: #ffffff;
		--bg-panel: #f8fafc;
		--border-panel: #e2e8f0;
		--text-primary: #0f172a;
		--text-secondary: #334155;
		--text-muted: #64748b;
		--text-dim: #94a3b8;
		--bg-input: #ffffff;
		--border-input: #cbd5e1;
		--bg-btn: #f1f5f9;
		--border-btn: #cbd5e1;
		--text-btn: #334155;
		--btn-hover-bg: #e2e8f0;
		--tree-hover-bg: #f1f5f9;
		--tree-selected-bg: #e0e7ff;
		--tree-selected-text: #4338ca;
		--code-bg: #f1f5f9;
		--code-color: #0284c7;
		--pre-bg: #f8fafc;
		--pre-border: #e2e8f0;
		--pre-text: #1e293b;
		--table-border: #e2e8f0;
		--th-bg: #f1f5f9;
		--th-text: #0f172a;
		--badge-bg: #f1f5f9;
		--badge-text: #475569;
		--branch-bg: #f1f5f9;
		--branch-text: #475569;
	}

	/* Header */
	.viewer-header {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 10px 16px;
		background-color: var(--bg-header);
		border-bottom: 1px solid var(--border-header);
		flex-shrink: 0;
	}

	.brand-zone {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.logo-badge {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 26px;
		height: 26px;
		background: linear-gradient(135deg, #6366f1, #a855f7);
		color: #ffffff;
		border-radius: 6px;
	}

	.brand-title {
		font-weight: 700;
		font-size: 14px;
		color: var(--text-primary);
	}

	.repo-tag {
		font-size: 11px;
		font-weight: 600;
		padding: 2px 6px;
		border-radius: 4px;
		background-color: var(--bg-viewport);
		color: #38bdf8;
		border: 1px solid #0284c7;
	}

	.branch-tag {
		font-size: 11px;
		padding: 2px 6px;
		border-radius: 4px;
		background-color: var(--branch-bg);
		color: var(--branch-text);
	}

	.breadcrumb-bar {
		display: flex;
		align-items: center;
		gap: 4px;
		font-size: 12px;
		margin-left: 12px;
		overflow-x: auto;
		white-space: nowrap;
	}

	.crumb-btn {
		background: none;
		border: none;
		color: var(--text-muted);
		cursor: pointer;
		padding: 2px 6px;
		border-radius: 4px;
		font-size: 12px;
	}

	.crumb-btn:hover {
		color: var(--text-primary);
		background-color: var(--btn-hover-bg);
	}

	.crumb-sep {
		color: var(--text-dim);
	}

	.crumb-current {
		color: var(--text-primary);
		font-weight: 600;
		padding: 2px 6px;
	}

	.action-zone {
		margin-left: auto;
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.mode-toggle-btn {
		background-color: var(--bg-btn);
		border: 1px solid var(--border-btn);
		color: var(--text-btn);
		padding: 4px 10px;
		border-radius: 6px;
		font-size: 12px;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.mode-toggle-btn:hover {
		background-color: var(--btn-hover-bg);
		color: var(--text-primary);
	}

	.mode-toggle-btn.active {
		background-color: #4f46e5;
		border-color: #6366f1;
		color: #ffffff;
	}

	.theme-toggle-btn {
		background-color: var(--bg-btn);
		border: 1px solid var(--border-btn);
		color: var(--text-btn);
		padding: 4px 10px;
		border-radius: 6px;
		font-size: 12px;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s ease;
		display: inline-flex;
		align-items: center;
		gap: 4px;
	}

	.theme-toggle-btn:hover {
		background-color: var(--btn-hover-bg);
		color: var(--text-primary);
	}

	/* Layout */
	.viewer-layout {
		display: flex;
		flex: 1;
		min-height: 0;
	}

	/* Sidebar */
	.sidebar-explorer {
		width: 280px;
		background-color: var(--bg-sidebar);
		border-right: 1px solid var(--border-sidebar);
		display: flex;
		flex-direction: column;
		flex-shrink: 0;
	}

	.sidebar-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 10px 12px;
		border-bottom: 1px solid var(--border-sidebar);
	}

	.section-label {
		font-size: 11px;
		font-weight: 700;
		color: var(--text-dim);
		letter-spacing: 0.05em;
	}

	.up-btn {
		background: none;
		border: 1px solid var(--border-input);
		color: var(--text-muted);
		font-size: 11px;
		padding: 2px 6px;
		border-radius: 4px;
		cursor: pointer;
	}

	.up-btn:hover {
		background-color: var(--tree-hover-bg);
		color: var(--text-primary);
	}

	.search-box {
		padding: 8px 12px;
		border-bottom: 1px solid var(--border-sidebar);
	}

	.filter-input {
		width: 100%;
		background-color: var(--bg-input);
		border: 1px solid var(--border-input);
		border-radius: 4px;
		padding: 6px 8px;
		font-size: 12px;
		color: var(--text-primary);
		outline: none;
	}

	.filter-input:focus {
		border-color: #6366f1;
	}

	.file-tree {
		flex: 1;
		overflow-y: auto;
		padding: 6px;
	}

	.tree-node {
		display: flex;
		align-items: center;
		gap: 8px;
		width: 100%;
		padding: 6px 8px;
		background: none;
		border: none;
		border-radius: 6px;
		color: var(--text-muted);
		font-size: 13px;
		cursor: pointer;
		text-align: left;
		transition: background-color 0.1s ease;
	}

	.tree-node:hover {
		background-color: var(--tree-hover-bg);
		color: var(--text-primary);
	}

	.tree-node.selected {
		background-color: var(--tree-selected-bg);
		color: var(--tree-selected-text);
		font-weight: 600;
	}

	.node-icon {
		font-size: 14px;
	}

	.node-name {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.loading-state,
	.empty-state {
		padding: 24px;
		text-align: center;
		font-size: 12px;
		color: var(--text-dim);
	}

	/* Viewport */
	.content-viewport {
		flex: 1;
		overflow-y: auto;
		background-color: var(--bg-viewport);
		padding: 24px 32px;
		position: relative;
	}

	.error-banner {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 10px 14px;
		background-color: #7f1d1d;
		border: 1px solid #b91c1c;
		border-radius: 6px;
		color: #fecaca;
		font-size: 13px;
		margin-bottom: 20px;
	}

	.loading-placeholder {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 300px;
		color: var(--text-muted);
	}

	.spinner {
		width: 32px;
		height: 32px;
		border: 3px solid var(--border-btn);
		border-top-color: #6366f1;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
		margin-bottom: 12px;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.document-container {
		max-width: 900px;
		margin: 0 auto;
	}

	.frontmatter-panel {
		background-color: var(--bg-panel);
		border: 1px solid var(--border-panel);
		border-radius: 8px;
		padding: 16px 20px;
		margin-bottom: 24px;
	}

	.fm-header {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 8px;
		margin-bottom: 10px;
	}

	.fm-id-badge {
		font-family: monospace;
		font-size: 12px;
		font-weight: 700;
		background-color: #1e1b4b;
		color: #a5b4fc;
		padding: 2px 8px;
		border-radius: 4px;
		border: 1px solid #4338ca;
	}

	.fm-status-badge {
		font-size: 11px;
		font-weight: 600;
		text-transform: uppercase;
		padding: 2px 8px;
		border-radius: 4px;
	}

	.status-accepted,
	.status-done {
		background-color: #064e3b;
		color: #6ee7b7;
	}

	.status-draft,
	.status-reviewing {
		background-color: #78350f;
		color: #fde68a;
	}

	.fm-badge {
		font-size: 11px;
		padding: 2px 8px;
		border-radius: 4px;
		background-color: var(--badge-bg);
		color: var(--badge-text);
	}

	.document-title {
		font-size: 20px;
		font-weight: 700;
		color: var(--text-primary);
		margin: 0;
	}

	.raw-content {
		background-color: var(--pre-bg);
		border: 1px solid var(--pre-border);
		border-radius: 8px;
		padding: 20px;
		overflow-x: auto;
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		font-size: 13px;
		line-height: 1.6;
		color: var(--pre-text);
	}

	/* Markdown Body Styles */
	.markdown-body {
		font-size: 15px;
		line-height: 1.7;
		color: var(--text-secondary);
	}

	.markdown-body :global(h1) {
		font-size: 26px;
		font-weight: 700;
		color: var(--text-primary);
		border-bottom: 1px solid var(--border-panel);
		padding-bottom: 8px;
		margin-top: 24px;
		margin-bottom: 16px;
	}

	.markdown-body :global(h2) {
		font-size: 20px;
		font-weight: 600;
		color: var(--text-primary);
		border-bottom: 1px solid var(--border-panel);
		padding-bottom: 6px;
		margin-top: 28px;
		margin-bottom: 14px;
	}

	.markdown-body :global(h3) {
		font-size: 16px;
		font-weight: 600;
		color: var(--text-primary);
		margin-top: 20px;
		margin-bottom: 10px;
	}

	.markdown-body :global(p) {
		margin-bottom: 16px;
	}

	.markdown-body :global(ul),
	.markdown-body :global(ol) {
		padding-left: 24px;
		margin-bottom: 16px;
	}

	.markdown-body :global(li) {
		margin-bottom: 6px;
	}

	.markdown-body :global(code) {
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		font-size: 13px;
		background-color: var(--code-bg);
		color: var(--code-color);
		padding: 2px 6px;
		border-radius: 4px;
	}

	.markdown-body :global(pre) {
		background-color: var(--pre-bg);
		border: 1px solid var(--pre-border);
		border-radius: 8px;
		padding: 16px;
		overflow-x: auto;
		margin-bottom: 16px;
	}

	.markdown-body :global(pre code) {
		background: none;
		color: var(--pre-text);
		padding: 0;
	}

	.markdown-body :global(table) {
		width: 100%;
		border-collapse: collapse;
		margin-bottom: 20px;
	}

	.markdown-body :global(th),
	.markdown-body :global(td) {
		border: 1px solid var(--table-border);
		padding: 8px 12px;
		font-size: 13px;
	}

	.markdown-body :global(th) {
		background-color: var(--th-bg);
		color: var(--th-text);
		font-weight: 600;
	}

	.markdown-body :global(blockquote) {
		border-left: 4px solid #6366f1;
		padding-left: 14px;
		margin: 16px 0;
		color: var(--text-muted);
	}

	/* Mermaid Diagram Container */
	.markdown-body :global(.mermaid-diagram) {
		position: relative;
		display: flex;
		flex-direction: column;
		margin: 24px 0;
		padding: 12px 16px 16px;
		border-radius: 8px;
		background-color: var(--bg-panel);
		border: 1px solid var(--border-panel);
		transition: border-color 0.15s ease;
	}

	.markdown-body :global(.mermaid-diagram:hover) {
		border-color: var(--border-btn);
	}

	.markdown-body :global(.diagram-toolbar) {
		display: flex;
		justify-content: flex-end;
		margin-bottom: 8px;
	}

	.markdown-body :global(.diagram-action-btn) {
		background-color: var(--bg-btn);
		border: 1px solid var(--border-btn);
		color: var(--text-btn);
		padding: 3px 8px;
		border-radius: 5px;
		font-size: 11px;
		font-weight: 500;
		cursor: pointer;
		display: inline-flex;
		align-items: center;
		gap: 4px;
		transition: all 0.15s ease;
		opacity: 0.75;
	}

	.markdown-body :global(.mermaid-diagram:hover .diagram-action-btn) {
		opacity: 1;
	}

	.markdown-body :global(.diagram-action-btn:hover) {
		background-color: var(--btn-hover-bg);
		color: var(--text-primary);
	}

	.markdown-body :global(.diagram-svg-wrap) {
		display: flex;
		justify-content: center;
		overflow-x: auto;
		width: 100%;
	}

	.markdown-body :global(.diagram-svg-wrap svg) {
		max-width: 100%;
		height: auto;
	}

	/* Fullscreen Diagram Modal */
	.diagram-modal-backdrop {
		position: fixed;
		inset: 0;
		z-index: 99999;
		background-color: rgba(0, 0, 0, 0.82);
		backdrop-filter: blur(8px);
		display: flex;
		flex-direction: column;
		padding: 16px;
		box-sizing: border-box;
		animation: fadeIn 0.15s ease;
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	.diagram-modal-window {
		display: flex;
		flex-direction: column;
		width: 100%;
		height: 100%;
		background-color: var(--bg-viewport);
		border: 1px solid var(--border-header);
		border-radius: 10px;
		overflow: hidden;
		box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
	}

	.modal-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 12px 18px;
		background-color: var(--bg-header);
		border-bottom: 1px solid var(--border-header);
		flex-shrink: 0;
	}

	.modal-title {
		font-size: 13px;
		font-weight: 600;
		color: var(--text-primary);
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.modal-controls {
		display: flex;
		align-items: center;
		gap: 6px;
	}

	.modal-btn {
		background-color: var(--bg-btn);
		border: 1px solid var(--border-btn);
		color: var(--text-btn);
		padding: 4px 10px;
		border-radius: 6px;
		font-size: 12px;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s ease;
		display: inline-flex;
		align-items: center;
		justify-content: center;
	}

	.modal-btn:hover {
		background-color: var(--btn-hover-bg);
		color: var(--text-primary);
	}

	.modal-btn.close-btn {
		background-color: #dc2626;
		border-color: #ef4444;
		color: #ffffff;
		margin-left: 8px;
	}

	.modal-btn.close-btn:hover {
		background-color: #b91c1c;
	}

	.zoom-indicator {
		font-size: 12px;
		font-weight: 600;
		color: var(--text-muted);
		min-width: 44px;
		text-align: center;
		user-select: none;
	}

	.modal-content {
		flex: 1;
		overflow: auto;
		padding: 32px;
		display: flex;
		align-items: center;
		justify-content: center;
		background-color: var(--bg-panel);
	}

	.modal-svg-canvas {
		transform-origin: center center;
		transition: transform 0.1s ease-out;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.modal-svg-canvas :global(svg) {
		max-width: none !important;
		height: auto !important;
	}

	/* Placeholder */
	.directory-placeholder {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		text-align: center;
		height: 400px;
		color: var(--text-dim);
	}

	.placeholder-icon {
		font-size: 48px;
		margin-bottom: 16px;
	}

	.directory-placeholder h2 {
		color: var(--text-primary);
		margin-bottom: 8px;
	}

	.quick-hints {
		display: flex;
		gap: 8px;
		margin-top: 16px;
	}

	.hint-pill {
		font-size: 11px;
		padding: 4px 10px;
		border-radius: 12px;
		background-color: var(--badge-bg);
		color: var(--badge-text);
	}
</style>
