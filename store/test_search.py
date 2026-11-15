from urllib.parse import parse_qs, urlsplit

from django.test import SimpleTestCase, override_settings
from django.urls import resolve, reverse

from .search import MAX_QUERY_LENGTH, SUGGESTION_LIMIT, search_context


class ClubSearchTests(SimpleTestCase):
    """Public navigation search must work without any database access."""

    def suggestions(self, query=''):
        return self.client.get(reverse('store_search_suggestions'), {'q': query})

    def test_landing_pages_have_search_link_panel_and_assets_once(self):
        for page in (reverse('store_home'), '/store/index2.html'):
            response = self.client.get(page)
            self.assertContains(response, 'data-store-search-open', count=1)
            self.assertContains(response, 'href="' + reverse('store_search') + '"')
            self.assertContains(response, 'id="store-search-dialog"', count=1)
            self.assertContains(response, 'shared/js/club-search.js', count=1)
            self.assertContains(response, 'shared/css/club-search.css', count=1)

    def test_empty_query_shows_bounded_popular_pages(self):
        data = self.suggestions().json()
        self.assertTrue(data['is_initial'])
        self.assertEqual(data['error'], '')
        self.assertTrue(0 < len(data['results']) <= SUGGESTION_LIMIT)

    def test_query_is_case_whitespace_and_width_normalized(self):
        for query in ('COACHES', '  coaches   ', 'ＣＯＡＣＨＥＳ'):
            data = self.suggestions(query).json()
            self.assertEqual(data['results'][0]['url'], reverse('store_coaches'))

    def test_aliases_prefixes_and_multiple_words_find_relevant_pages(self):
        for query, route in [('soccer', 'store_games'), ('mem', 'store_signup'), ('sign up', 'store_signup'),
                             ('sign in', 'store_login'), ('help', 'store_contact'), ('trainer', 'store_coaches'),
                             ('football training', 'store_coaches'), ('Denial Sork', 'store_coaches')]:
            with self.subTest(query=query):
                results = self.suggestions(query).json()['results']
                self.assertTrue(results)
                self.assertEqual(results[0]['url'], reverse(route))

    def test_title_matches_rank_before_other_matches(self):
        results = search_context('about')['results']
        self.assertEqual(results[0]['title'], 'About the club')

    def test_each_word_must_match(self):
        self.assertEqual(search_context('coaches zzznotfound')['results'], [])

    def test_single_character_gets_guidance_instead_of_broad_results(self):
        data = self.suggestions('a').json()
        self.assertEqual(data['results'], [])
        self.assertIn('at least 2', data['error'])

    def test_long_and_expanding_unicode_queries_are_bounded(self):
        for query in ('x' * (MAX_QUERY_LENGTH + 1), '\ufb03' * MAX_QUERY_LENGTH, ' ' * (MAX_QUERY_LENGTH + 1)):
            data = self.suggestions(query).json()
            self.assertIn('120', data['error'])
            self.assertEqual(data['results'], [])
            self.assertLessEqual(len(data['query']), MAX_QUERY_LENGTH)

    def test_no_results_and_typo_suggestion(self):
        data = self.suggestions('coahces').json()
        self.assertEqual(data['results'], [])
        self.assertEqual(data['did_you_mean'], 'coaches')
        self.assertEqual(search_context(data['did_you_mean'])['results'][0]['url'], reverse('store_coaches'))
        self.assertEqual(self.suggestions('zzzzzzzzzz').json()['did_you_mean'], '')

    def test_shop_link_uses_existing_search_with_encoded_query(self):
        data = self.suggestions('jersey & shorts').json()
        url = urlsplit(data['shop_search_url'])
        self.assertEqual(url.path, reverse('Search'))
        self.assertEqual(parse_qs(url.query)['search'], ['jersey & shorts'])

    @override_settings(ROOT_URLCONF='store.urls')
    def test_optional_shop_routes_are_not_required(self):
        data = search_context('football')
        self.assertEqual(data['shop_search_url'], '')
        self.assertTrue(data['results'])
        self.assertFalse(any(result['category'] == 'Shop' for result in data['results']))

    def test_highlighting_preserves_plain_text(self):
        result = search_context('coach')['results'][0]
        self.assertTrue(any(part['match'] for part in result['title_parts']))
        self.assertEqual(''.join(part['text'] for part in result['title_parts']), result['title'])

    def test_query_html_is_escaped_in_full_results(self):
        query = '<script>alert(1)</script>'
        response = self.client.get(reverse('store_search'), {'q': query})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, query)
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')

    def test_full_results_page_and_no_javascript_form(self):
        response = self.client.get(reverse('store_search'), {'q': 'membership'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="q"')
        self.assertContains(response, 'Join the club')
        self.assertContains(response, reverse('store_signup'))
        self.assertContains(response, 'id="store-search-dialog"', count=1)

    def test_blank_and_unmatched_full_results_have_clear_states(self):
        self.assertContains(self.client.get(reverse('store_search')), 'Popular pages')
        self.assertContains(self.client.get(reverse('store_search'), {'q': 'zzzzzzzzzz'}), 'No club pages found')

    def test_endpoint_is_read_only_and_suggestions_are_not_cached(self):
        self.assertEqual(self.client.post(reverse('store_search_suggestions'), {'q': 'coach'}).status_code, 405)
        self.assertEqual(self.client.post(reverse('store_search'), {'q': 'coach'}).status_code, 405)
        self.assertEqual(self.suggestions('coaches')['Cache-Control'], 'no-store')

    def test_results_only_link_to_public_pages_and_do_not_expose_models(self):
        allowed = {'store_games', 'store_coaches', 'store_signup', 'store_about', 'store_contact', 'store_login', 'ShopHome'}
        for query in ('', 'club', 'football', 'profile', 'admin', 'payment', 'password'):
            for result in search_context(query)['results']:
                self.assertIn(resolve(result['url']).url_name, allowed)
                self.assertEqual(set(result), {'title', 'description', 'category', 'url', 'title_parts', 'description_parts'})
