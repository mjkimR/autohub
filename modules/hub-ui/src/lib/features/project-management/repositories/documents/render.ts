import { marked } from 'marked';
import DOMPurify from 'dompurify';
import { headingSlug, resolveRepositoryLink, type RepositoryDocument } from './model';

export function renderRepositoryMarkdown(doc: RepositoryDocument) {
	const root = document.createElement('div');
	root.innerHTML = DOMPurify.sanitize(
		marked.parse(doc.body, { async: false, gfm: true }) as string,
		{ USE_PROFILES: { html: true }, ALLOW_DATA_ATTR: false }
	);
	const headings: { id: string; title: string }[] = [];
	const seen = new Map<string, number>();
	for (const heading of root.querySelectorAll('h1,h2,h3,h4,h5,h6')) {
		const title = heading.textContent || '';
		const slug = headingSlug(title),
			count = seen.get(slug) || 0;
		seen.set(slug, count + 1);
		heading.id = count ? `${slug}-${count}` : slug;
		heading.setAttribute('tabindex', '-1');
		headings.push({ id: heading.id, title });
	}
	for (const link of root.querySelectorAll<HTMLAnchorElement>('a[href]')) {
		const href = link.getAttribute('href') || '';
		if (/^https?:\/\//i.test(href)) {
			link.target = '_blank';
			link.rel = 'noopener noreferrer';
			continue;
		}
		if (/^mailto:/i.test(href)) continue;
		const location = resolveRepositoryLink(doc.path, href);
		if (location) {
			link.dataset.repositoryPath = location.path;
			link.dataset.fragment = location.fragment;
			link.dataset.repositoryDirectory = String(location.directory);
			link.href = '#';
		} else {
			link.removeAttribute('href');
			link.setAttribute('aria-disabled', 'true');
		}
	}
	for (const code of root.querySelectorAll('code')) {
		if (code.closest('pre, a')) continue;
		const id = code.textContent?.trim() || '';
		if (!/^(?:CAP|UC|ADR|SPEC|PROP|MS|UX|ARCH|FB|PLAN|TASKS)-[\w.-]+$/.test(id)) continue;
		const link = document.createElement('a');
		link.href = '#';
		link.dataset.documentId = id;
		code.replaceWith(link);
		link.append(code);
	}
	// Relative images cannot bypass the authenticated repository transport.
	for (const image of root.querySelectorAll('img')) {
		const src = image.getAttribute('src') || '';
		if (!/^https:\/\//i.test(src))
			image.replaceWith(document.createTextNode(image.alt || 'Repository image'));
	}
	return { html: root.innerHTML, headings };
}
