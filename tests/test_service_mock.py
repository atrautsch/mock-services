import json
import logging
import unittest

import attr

from requests import Request

import requests

import responses

from mock_services import reset_rules
from mock_services import start_http_mock
from mock_services import stop_http_mock
from mock_services import update_rest_rules


CONTENTTYPE_JSON = {'content-type': 'application/json'}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(name)s  %(message)s'
)

rest_rules = [
    {
        'method': 'LIST',
        'url': r'^http://my_fake_service/(?P<resource>api)$'
    },
    {
        'method': 'GET',
        'url': r'^http://my_fake_service/(?P<resource>api)/(?P<id>\d+)$',
    },
    {
        'method': 'GET',
        'url': r'^http://my_fake_service/(?P<resource>api)/(?P<id>\d+)/(?P<action>download)$',  # noqa
    },
    {
        'method': 'POST',
        'url': r'^http://my_fake_service/(?P<resource>api)$',
        'id_name': 'id',
        'id_factory': int,
        'attrs': {
            'bar': attr.ib(),
            'foo':attr.ib(default=True)
        }
    },
    {
        'method': 'PATCH',
        'url': r'^http://my_fake_service/(?P<resource>api)/(?P<id>\d+)$',
    },
    {
        'method': 'DELETE',
        'url': r'^http://my_fake_service/(?P<resource>api)/(?P<id>\d+)$'
    },
]


class ResponsesHelpersServiceTestCase(unittest.TestCase):

    def setUp(self):
        stop_http_mock()
        reset_rules()

    tearDown = setUp

    def test_update_rules(self):

        self.assertFalse(responses._default_mock._urls)

        update_rest_rules(rest_rules)

        self.assertEqual(len(responses._default_mock._urls), 6)
        for rule in responses._default_mock._urls:
            self.assertEqual(sorted(rule.keys()), [
                'callback',
                'content_type',
                'match_querystring',
                'method',
                'url',
            ])

        list_rule = responses._default_mock._urls[0]

        self.assertTrue(hasattr(list_rule['url'], 'match'))
        self.assertTrue(list_rule['url'].match('http://my_fake_service/api'))
        self.assertTrue(hasattr(list_rule['callback'], '__call__'))
        self.assertEqual(list_rule['method'], 'GET')
        self.assertEqual(list_rule['content_type'], 'application/json')

        get_rule = responses._default_mock._urls[1]

        self.assertTrue(hasattr(get_rule['url'], 'match'))
        self.assertTrue(get_rule['url'].match('http://my_fake_service/api/1'))
        self.assertTrue(hasattr(get_rule['callback'], '__call__'))
        self.assertEqual(get_rule['method'], 'GET')
        self.assertEqual(get_rule['content_type'], 'application/json')

        patch_rule = responses._default_mock._urls[2]

        self.assertTrue(hasattr(patch_rule['url'], 'match'))
        self.assertTrue(patch_rule['url'].match('http://my_fake_service/api/1/download'))  # noqa
        self.assertTrue(hasattr(patch_rule['callback'], '__call__'))
        self.assertEqual(patch_rule['method'], 'GET')
        self.assertEqual(patch_rule['content_type'], 'application/json')

        post_rule = responses._default_mock._urls[3]

        self.assertTrue(hasattr(post_rule['url'], 'match'))
        self.assertTrue(post_rule['url'].match('http://my_fake_service/api'))
        self.assertTrue(hasattr(post_rule['callback'], '__call__'))
        self.assertEqual(post_rule['method'], 'POST')
        self.assertEqual(post_rule['content_type'], 'application/json')

        patch_rule = responses._default_mock._urls[4]

        self.assertTrue(hasattr(patch_rule['url'], 'match'))
        self.assertTrue(patch_rule['url'].match('http://my_fake_service/api/1'))  # noqa
        self.assertTrue(hasattr(patch_rule['callback'], '__call__'))
        self.assertEqual(patch_rule['method'], 'PATCH')
        self.assertEqual(patch_rule['content_type'], 'application/json')

        delete_rule = responses._default_mock._urls[5]

        self.assertTrue(hasattr(delete_rule['url'], 'match'))
        self.assertTrue(delete_rule['url'].match('http://my_fake_service/api/1'))  # noqa
        self.assertTrue(hasattr(delete_rule['callback'], '__call__'))
        self.assertEqual(delete_rule['method'], 'DELETE')
        self.assertEqual(delete_rule['content_type'], 'application/json')

    def test_rest_rules_cb(self):

        url = 'http://my_fake_service/api'

        update_rest_rules(rest_rules)
        self.assertTrue(start_http_mock())

        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers, {'content-type': 'application/json'})
        self.assertEqual(r.json(), [])

        r = requests.get(url + '/1')
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.headers, {'content-type': 'application/json'})
        self.assertEqual(r.json(), {'error': 'not found'})

        r = requests.get(url + '/1/download')
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.headers, {'content-type': 'application/json'})
        self.assertEqual(r.json(), {'error': 'not found'})

        r = requests.post(url, data=json.dumps({}), headers=CONTENTTYPE_JSON)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.headers, {'content-type': 'application/json'})
        self.assertEqual(r.json(), {'error': 'validation error'})

        r = requests.patch(url + '/1', data=json.dumps({}))
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.headers, {'content-type': 'application/json'})
        self.assertEqual(r.json(), {'error': 'not found'})

        r = requests.delete(url + '/1')
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.headers, {'content-type': 'application/json'})
        self.assertEqual(r.json(), {'error': 'not found'})

        # add some data

        r = requests.post(url, data=json.dumps({
            'bar': 'Python will save the world.',
        }), headers=CONTENTTYPE_JSON)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.headers, {'content-type': 'application/json'})
        self.assertEqual(r.json(), {
            'id': 1,
            'foo': True,
            'bar': 'Python will save the world.',
        })

        # recheck list get ...

        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers, {'content-type': 'application/json'})
        self.assertEqual(r.json(), [
            {
                'id': 1,
                'foo': True,
                'bar': 'Python will save the world.',
            }
        ])

        r = requests.patch(url + '/1', data=json.dumps({
            'bar': "Python will save the world. I don't know how. But it will."
        }))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers, {'content-type': 'application/json'})
        self.assertEqual(r.json(), {
            'id': 1,
            'foo': True,
            'bar': "Python will save the world. I don't know how. But it will.",
        })

        r = requests.get(url + '/1')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers, {'content-type': 'application/json'})
        self.assertEqual(r.json(), {
            'id': 1,
            'foo': True,
            'bar': "Python will save the world. I don't know how. But it will.",
        })

        r = requests.delete(url + '/1')
        self.assertEqual(r.status_code, 204)
        self.assertEqual(r.headers, {'content-type': 'application/json'})
        self.assertEqual(r.json(), {})

        r = requests.get(url + '/1')
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.headers, {'content-type': 'application/json'})
        self.assertEqual(r.json(), {
            'error': 'not found'
        })