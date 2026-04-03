import { getCollection } from 'astro:content';

const SITE = 'https://nasdaq-blog.nextfintechai.com';
const getSlug = (id) => id.replace(/\.[^/.]+$/, '');

export async function GET() {
	const posts = await getCollection('blog');

	const staticUrls = ['/', '/about/', '/blog/', '/seo/', '/rss.xml'];
	const postUrls = posts.map((post) => `/blog/${getSlug(post.id)}/`);
	const allUrls = [...staticUrls, ...postUrls];

	const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${allUrls.map((path) => `  <url><loc>${SITE}${path}</loc></url>`).join('\n')}
</urlset>`;

	return new Response(xml, {
		headers: {
			'Content-Type': 'application/xml; charset=utf-8',
		},
	});
}
