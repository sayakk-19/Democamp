"""Search public club navigation without querying membership or payment data."""

import re
import unicodedata
from difflib import get_close_matches
from urllib.parse import urlencode

from django.http import JsonResponse
from django.shortcuts import render
from django.urls import NoReverseMatch, reverse
from django.views.decorators.http import require_GET


MIN_QUERY_LENGTH = 2
MAX_QUERY_LENGTH = 120
SUGGESTION_LIMIT = 6
STOP_WORDS = {'a', 'an', 'and', 'for', 'of', 'our', 'the', 'to'}

PAGES = (
    {'title': 'Sports & games', 'description': 'Explore football, ball control, passing and teamwork at the club.',
     'route': 'store_games', 'category': 'Sports', 'keywords': 'football soccer ball games match pitch warm up fitness skills sport'},
    {'title': 'Coaches & training', 'description': 'Meet the club coaches and learn about focused practice and steady improvement.',
     'route': 'store_coaches', 'category': 'Training', 'keywords': 'coach coaches trainer trainers trannir tranner training practice football soccer guidance conditioning Denial Sork'},
    {'title': 'Join the club', 'description': 'Complete your membership application and submit your details for approval.',
     'route': 'store_signup', 'category': 'Membership', 'keywords': 'join membership member members registration register signup sign up application age position phone'},
    {'title': 'About the club', 'description': 'Learn about the club, teamwork, fair play and enjoying sport together.',
     'route': 'store_about', 'category': 'Club', 'keywords': 'about club community values mission story information'},
    {'title': 'Contact us', 'description': 'Find the contact page for club questions and membership enquiries.',
     'route': 'store_contact', 'category': 'Help', 'keywords': 'contact help support email phone question enquiry location get in touch'},
    {'title': 'Sports shop', 'description': 'Browse sports products, equipment and clothing in the shop.',
     'route': 'ShopHome', 'category': 'Shop', 'keywords': 'shop store product products equipment gear kit jersey jerseys ball football clothing cart buy'},
    {'title': 'Log in', 'description': 'Sign in to access your club profile and display settings.',
     'route': 'store_login', 'category': 'Account', 'keywords': 'login log in signin sign in account profile settings password night dark mode google github twitter'},
)


def normalize(value):
    return ' '.join(unicodedata.normalize('NFKC', value).split())


def words(value):
    return re.findall(r'\w+', normalize(value).casefold(), flags=re.UNICODE)


def highlight(value, tokens):
    """Return plain segments; templates escape every segment normally."""
    if not tokens:
        return [{'text': value, 'match': False}]
    pattern = re.compile('(' + '|'.join(re.escape(token) for token in sorted(tokens, key=len, reverse=True)) + ')', re.IGNORECASE)
    return [{'text': piece, 'match': bool(index % 2)} for index, piece in enumerate(pattern.split(value)) if piece]


def public_pages():
    result = []
    for page in PAGES:
        try:
            url = reverse(page['route'])
        except NoReverseMatch:
            continue
        result.append({**page, 'url': url})
    return result


def search_context(raw_query):
    raw_query = raw_query or ''
    normalized = normalize(raw_query[:MAX_QUERY_LENGTH + 1])
    too_long = len(raw_query) > MAX_QUERY_LENGTH or len(normalized) > MAX_QUERY_LENGTH
    query = normalized[:MAX_QUERY_LENGTH]
    too_short = bool(query) and len(query) < MIN_QUERY_LENGTH
    tokens = list(dict.fromkeys(token for token in words(query) if token not in STOP_WORDS))[:12]
    pages = public_pages()
    results = []
    if not query and not too_long:
        results = pages[:SUGGESTION_LIMIT]
    elif not too_short and not too_long and tokens:
        ranked = []
        for position, page in enumerate(pages):
            title = normalize(page['title']).casefold()
            title_words = words(page['title'])
            keyword_words = words(page['keywords'])
            description_words = words(page['description'])
            all_words = title_words + keyword_words + description_words
            if not all(any(word.startswith(token) for word in all_words) for token in tokens):
                continue
            score = 100 if title == query.casefold() else 50 if title.startswith(query.casefold()) else 0
            for token in tokens:
                score += 12 if token in title_words else 8 if any(word.startswith(token) for word in title_words) else 0
                score += 5 if token in keyword_words else 3 if any(word.startswith(token) for word in keyword_words) else 0
                score += 1 if any(word.startswith(token) for word in description_words) else 0
            ranked.append((-score, position, page))
        results = [page for _, _, page in sorted(ranked, key=lambda item: (item[0], item[1]))]
    did_you_mean = ''
    if query and tokens and not results and not too_short and not too_long:
        vocabulary = sorted({word for page in pages for word in words(page['title'] + ' ' + page['keywords']) if len(word) > 2})
        corrected = []
        for token in tokens:
            matches = get_close_matches(token, vocabulary, n=1, cutoff=0.8) if token not in vocabulary and len(token) > 2 else []
            corrected.append(matches[0] if matches else token)
        candidate = ' '.join(corrected)
        if candidate != ' '.join(tokens):
            did_you_mean = candidate
    error = ''
    if too_long:
        error = 'Please keep your search to 120 characters or fewer.'
    elif too_short:
        error = 'Type at least 2 characters to search.'
    shop_search_url = ''
    if query and not error:
        try:
            shop_search_url = reverse('Search') + '?' + urlencode({'search': query})
        except NoReverseMatch:
            pass
    public_results = [
        {'title': page['title'], 'description': page['description'], 'category': page['category'], 'url': page['url'],
         'title_parts': highlight(page['title'], tokens), 'description_parts': highlight(page['description'], tokens)}
        for page in results
    ]
    return {'query': query, 'results': public_results, 'total': len(public_results), 'error': error,
            'did_you_mean': did_you_mean, 'shop_search_url': shop_search_url, 'is_initial': not query}


@require_GET
def search_results(request):
    return render(request, 'store/search_results.html', search_context(request.GET.get('q', '')))


@require_GET
def suggestions(request):
    context = search_context(request.GET.get('q', ''))
    context['results'] = context['results'][:SUGGESTION_LIMIT]
    response = JsonResponse(context)
    response['Cache-Control'] = 'no-store'
    return response
