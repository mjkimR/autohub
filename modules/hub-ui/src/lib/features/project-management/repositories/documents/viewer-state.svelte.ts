import { SvelteMap } from 'svelte/reactivity';
import type { RepositoryDataSource } from '../data-source';
import type { RepoBlob, RepoItem } from '../types';
import { discoverDocuments, listChildren } from './discovery';
import { loadHandbook, type HandbookManifest } from './handbook';
import { safePath, type DocumentListing, type DocumentSection } from './model';

const message = (error: unknown) => (error instanceof Error ? error.message : String(error));
export class DocumentViewerState {
	section = $state<DocumentSection>('documents');
	listing = $state<DocumentListing>({ documents: [], errors: [] });
	query = $state('');
	blob = $state<RepoBlob | null>(null);
	files = $state<RepoItem[]>([]);
	directory = $state('');
	fragment = $state('');
	loading = $state(false);
	reading = $state(false);
	error = $state('');
	readError = $state('');
	manifest = $state<HandbookManifest | null>(null);
	language = $state('en');
	requestedPath = $state('');
	private source!: RepositoryDataSource;
	private ref = '';
	private requestedReference = '';
	private controller = new AbortController();
	private readController = new AbortController();
	private generation = 0;
	private readGeneration = 0;
	private cache = new SvelteMap<DocumentSection | 'references', DocumentListing>();
	private selected: (path: string) => void;
	constructor(selected: (path: string) => void) {
		this.selected = selected;
	}

	configure(source: RepositoryDataSource, ref: string, initialPath: string) {
		this.destroy();
		this.source = source;
		this.ref = ref;
		this.cache.clear();
		this.query = '';
		this.blob = null;
		this.readError = '';
		this.requestedPath = '';
		void this.changeSection(initialPath ? 'files' : 'documents', initialPath);
	}
	async changeSection(section: DocumentSection, initialPath = '') {
		this.controller.abort();
		this.controller = new AbortController();
		this.readController.abort();
		++this.readGeneration;
		this.reading = false;
		const signal = this.controller.signal,
			generation = ++this.generation;
		this.section = section;
		this.query = '';
		this.blob = null;
		this.files = [];
		this.directory = '';
		this.manifest = null;
		this.error = '';
		this.readError = '';
		this.requestedPath = '';
		this.listing = { documents: [], errors: [] };
		this.loading = true;
		if (!initialPath) this.selected('');
		try {
			if (section === 'handbook') {
				const manifest = await loadHandbook(this.source, this.ref, signal);
				if (generation !== this.generation) return;
				this.manifest = manifest;
				this.language = manifest?.langs.includes(this.language) ? this.language : 'en';
				if (manifest) void this.open(`handbook/${this.language}/README.md`);
			} else if (section === 'files') {
				if (initialPath) void this.open(initialPath);
				else await this.loadDirectory('', signal, generation);
			} else {
				const listing =
					this.cache.get(section) ||
					(await discoverDocuments(this.source, this.ref, section, signal));
				if (generation !== this.generation) return;
				this.listing = listing;
				if (!listing.errors.length) this.cache.set(section, listing);
			}
		} catch (error) {
			if (generation === this.generation && !signal.aborted) this.error = message(error);
		} finally {
			if (generation === this.generation) this.loading = false;
		}
	}
	private async loadDirectory(path: string, signal: AbortSignal, generation: number) {
		if (path && !safePath(path)) throw new Error('Invalid repository directory');
		const files = await listChildren(this.source, path, this.ref, signal);
		if (generation !== this.generation || signal.aborted) return;
		this.files = files;
		this.directory = path;
	}
	async directoryTo(path: string) {
		this.section = 'files';
		this.controller.abort();
		this.controller = new AbortController();
		this.readController.abort();
		++this.readGeneration;
		this.reading = false;
		const generation = ++this.generation,
			signal = this.controller.signal;
		this.blob = null;
		this.files = [];
		this.directory = path;
		this.readError = '';
		this.requestedPath = '';
		this.error = '';
		this.loading = true;
		this.selected('');
		try {
			await this.loadDirectory(path, signal, generation);
		} catch (error) {
			if (generation === this.generation && !signal.aborted) this.error = message(error);
		} finally {
			if (generation === this.generation) this.loading = false;
		}
	}
	private async fileDirectory(path: string) {
		this.controller.abort();
		this.controller = new AbortController();
		const generation = ++this.generation,
			signal = this.controller.signal;
		this.directory = path.split('/').slice(0, -1).join('/');
		this.files = [];
		this.error = '';
		this.loading = true;
		try {
			await this.loadDirectory(this.directory, signal, generation);
		} catch (error) {
			if (generation === this.generation && !signal.aborted) this.error = message(error);
		} finally {
			if (generation === this.generation) this.loading = false;
		}
	}

	async open(path: string, fragment = '') {
		this.readController.abort();
		this.readController = new AbortController();
		const generation = ++this.readGeneration,
			signal = this.readController.signal;
		this.blob = null;
		this.readError = '';
		this.requestedPath = path;
		this.requestedReference = '';
		this.fragment = fragment;
		this.reading = true;
		this.selected('');
		try {
			if (!safePath(path)) throw new Error('Invalid repository path');
			if (this.section === 'files') void this.fileDirectory(path);
			const blob = await this.source.blob(path, this.ref, signal);
			if (generation !== this.readGeneration || signal.aborted) return;
			this.blob = blob;
			this.selected(path);
		} catch (error) {
			if (generation === this.readGeneration && !signal.aborted)
				this.readError = `${path}: ${message(error)}`;
		} finally {
			if (generation === this.readGeneration) this.reading = false;
		}
	}
	async reference(id: string) {
		this.requestedReference = id;
		this.readController.abort();
		this.readController = new AbortController();
		const generation = ++this.readGeneration,
			signal = this.readController.signal;
		this.readError = '';
		this.reading = true;
		try {
			const sections = ['documents', 'specs'] as const;
			const listings = [];
			for (const section of sections) {
				const key = section === 'documents' ? 'references' : section;
				const result =
					this.cache.get(key) ||
					(await discoverDocuments(
						this.source,
						this.ref,
						section,
						signal,
						section === 'documents'
					));
				if (generation !== this.readGeneration || signal.aborted) return;
				if (!result.errors.length) this.cache.set(key, result);
				listings.push(result);
			}
			if (listings.some((listing) => listing.errors.length))
				throw new Error(`Cannot resolve ${id}: document index is incomplete`);
			const matches = listings
				.flatMap((listing) => listing.documents)
				.filter((doc) => doc.id === id);
			if (matches.length !== 1)
				throw new Error(
					`${id}: ${matches.length ? 'Document ID is ambiguous' : 'Document ID not found'}`
				);
			void this.open(matches[0].path);
		} catch (error) {
			if (generation === this.readGeneration && !signal.aborted) this.readError = message(error);
		} finally {
			if (generation === this.readGeneration) this.reading = false;
		}
	}
	async chooseLanguage(language: string) {
		this.language = language;
		await this.open(`handbook/${language}/README.md`);
	}
	retryRead() {
		if (this.requestedReference) {
			this.cache.clear();
			void this.reference(this.requestedReference);
		} else void this.open(this.requestedPath, this.fragment);
	}
	retry() {
		if (this.section === 'files') {
			void this.directoryTo(this.directory);
			return;
		}
		this.cache.delete(this.section);
		void this.changeSection(this.section);
	}
	destroy() {
		this.controller.abort();
		this.readController.abort();
		++this.generation;
		++this.readGeneration;
	}
}
