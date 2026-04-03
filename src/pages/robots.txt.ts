export function GET() {
	const body = `User-agent: *
Allow: /
Sitemap: https://nasdaq-blog.nextfintechai.com/sitemap.xml
Sitemap: https://nasdaq-blog.nextfintechai.com/sitemap-index.xml
`;

	return new Response(body, {
		headers: {
			'Content-Type': 'text/plain; charset=utf-8',
		},
	});
}
