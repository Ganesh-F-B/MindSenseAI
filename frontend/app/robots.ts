import { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: ['/', '/privacy', '/terms', '/safety'],
        disallow: [
          '/chat',
          '/chat/*',
          '/dashboard',
          '/dashboard/*',
          '/profile',
          '/profile/*',
          '/settings',
          '/settings/*',
          '/analytics',
          '/analytics/*',
          '/login',
          '/signup',
          '/api/*',
        ],
      },
    ],
    sitemap: 'https://mindsenseai.org/sitemap.xml',
  };
}
