import unittest
from unittest.mock import patch
from urllib.parse import urlparse,parse_qs
import catalog as c
import app

class CatalogTests(unittest.TestCase):
    def test_complete_snapshot_and_prices(self):
        d=c.catalog();self.assertEqual(d['summary']['entries'],len(d['entries']));self.assertEqual(len(d['entries']),1171)
        self.assertEqual(d['summary']['free_access'],1040)
        self.assertEqual(sum(d['summary']['pricing'].values()),1171)
        self.assertEqual(len({e['id'] for e in d['entries']}),1171)
    def test_default_filter_excludes_paid_and_unknown(self):
        d=c.query_catalog({});self.assertEqual(d['total'],1040)
        self.assertTrue(all(x['pricing'] in c.FREE_PRICING for x in d['entries']))
    def test_search_category_and_pagination(self):
        d=c.query_catalog({'q':'Open Library','pricing':'all'});self.assertTrue(any(x['name']=='Open Library' for x in d['entries']))
        first=c.query_catalog({});second=c.query_catalog({'offset':30})
        self.assertFalse(set(x['id'] for x in first['entries'])&set(x['id'] for x in second['entries']))
        category=first['entries'][0]['category'][0]
        self.assertTrue(all(x['category'][0]==category for x in c.query_catalog({'category':category})['entries']))
    def test_index_search_never_opens_original_provider_or_template(self):
        entry=next(x for x in c.catalog()['entries'] if '<username>' in x['url'] and x['pricing'] in c.FREE_PRICING)
        url=c.indexed_source_url(entry['id'],'example user')
        self.assertEqual(urlparse(url).hostname,'www.google.com');self.assertIn('site:',parse_qs(urlparse(url).query)['q'][0])
        self.assertNotIn('<username>',url)
    def test_invalid_queries_and_sources(self):
        entry=c.query_catalog({})['entries'][0]
        for q in ['',None,'x'*241,'line\nbreak']:
            with self.assertRaises(ValueError):c.indexed_source_url(entry['id'],q)
        paid=next(x for x in c.catalog()['entries'] if x['pricing']=='paid')
        for source_id in ['missing',paid['id']]:
            with self.assertRaises(ValueError):c.indexed_source_url(source_id,'example')
    def test_unknown_and_local_are_not_automatically_integrated(self):
        for row in c.catalog()['entries']:
            if row['pricing']=='unknown':self.assertEqual(row['integration'],'unverified')
            if row['local_install']:self.assertNotEqual(row['integration'],'integrated')
    def test_books_adapter_parses_metadata_only(self):
        payload={'docs':[{'title':'Example','author_name':['Author'],'first_publish_year':2020,'cover_i':123}]}
        with patch.object(app,'get_json',return_value=payload) as call:
            url,rows=app.books('example');self.assertEqual(urlparse(url).hostname,'openlibrary.org');self.assertEqual(len(rows),1)
            self.assertIn('2020',rows[0]['detail']);self.assertNotIn('cover',str(rows));self.assertEqual(call.call_count,1)
    def test_new_links_are_reviewed_indices(self):
        for kind,value in [('topic','Example'),('username','example'),('domain','example.com')]:
            self.assertTrue(all(app.allowed_external(x['url']) for x in app.prepared_links(kind,value)))
        for url in ['https://openlibrary.org/people/user','https://pubmed.ncbi.nlm.nih.gov/1','https://duckduckgo.com/aichat','https://www.google.com/maps']:
            self.assertFalse(app.allowed_external(url))
