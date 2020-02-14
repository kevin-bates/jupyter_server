import time
import json
import pytest


import tornado
import urllib.parse
from tornado.escape import url_escape

from jupyter_server.utils import url_path_join
from ...utils import expected_http_error

from ipython_genutils.py3compat import PY3
NATIVE_KERNEL_NAME = 'python3' if PY3 else 'python2'

@pytest.fixture
def ws_fetch(auth_header, http_port):
    """fetch fixture that handles auth, base_url, and path"""
    def client_fetch(*parts, headers={}, params={}, **kwargs):
        # Handle URL strings
        path = url_escape(url_path_join(*parts), plus=False)
        urlparts = urllib.parse.urlparse('ws://localhost:{}'.format(http_port))
        urlparts = urlparts._replace(
            path=path,
            query=urllib.parse.urlencode(params)
        )
        url = urlparts.geturl()
        # Add auth keys to header
        headers.update(auth_header)
        # Make request.
        req = tornado.httpclient.HTTPRequest(
            url,
            headers=auth_header,
            connect_timeout=120
        )
        return tornado.websocket.websocket_connect(req)
    return client_fetch


async def test_no_kernels(fetch):
    r = await fetch(
        'api', 'kernels',
        method='GET'
    )
    kernels = json.loads(r.body.decode())
    assert kernels == []


async def test_default_kernels(fetch):
    r = await fetch(
        'api', 'kernels',
        method='POST',
        allow_nonstandard_methods=True
    )
    kernel = json.loads(r.body.decode())
    assert r.headers['location'] == '/api/kernels/' + kernel['id']
    assert r.code == 201
    assert isinstance(kernel, dict)

    report_uri = '/api/security/csp-report'
    expected_csp = '; '.join([
        "frame-ancestors 'self'",
        'report-uri ' + report_uri,
        "default-src 'none'"
    ])
    assert r.headers['Content-Security-Policy'] == expected_csp


async def test_main_kernel_handler(fetch):
    # Start the first kernel
    r = await fetch(
        'api', 'kernels',
        method='POST',
        body=json.dumps({
            'name': 'pyimport/kernel'
        })
    )
    kernel1 = json.loads(r.body.decode())
    assert r.headers['location'] == '/api/kernels/' + kernel1['id']
    assert r.code == 201
    assert isinstance(kernel1, dict)

    report_uri = '/api/security/csp-report'
    expected_csp = '; '.join([
        "frame-ancestors 'self'",
        'report-uri ' + report_uri,
        "default-src 'none'"
    ])
    assert r.headers['Content-Security-Policy'] == expected_csp

    # Check that the kernel is found in the kernel list
    r = await fetch(
        'api', 'kernels',
        method='GET'
    )
    kernel_list = json.loads(r.body.decode())
    assert r.code == 200
    assert isinstance(kernel_list, list)
    assert kernel_list[0]['id'] == kernel1['id']
    assert kernel_list[0]['name'] == kernel1['name']

    # Start a second kernel
    r = await fetch(
        'api', 'kernels',
        method='POST',
        body=json.dumps({
            'name': 'pyimport/kernel'
        })
    )
    kernel2 = json.loads(r.body.decode())
    assert isinstance(kernel2, dict)

    # Get kernel list again
    r = await fetch(
        'api', 'kernels',
        method='GET'
    )
    kernel_list = json.loads(r.body.decode())
    assert r.code == 200
    assert isinstance(kernel_list, list)
    assert len(kernel_list) == 2

    # Interrupt a kernel
    r = await fetch(
        'api', 'kernels', kernel2['id'], 'interrupt',
        method='POST',
        allow_nonstandard_methods=True
    )
    assert r.code == 204

    # Restart a kernel
    r = await fetch(
        'api', 'kernels', kernel2['id'], 'restart',
        method='POST',
        allow_nonstandard_methods=True
    )
    restarted_kernel = json.loads(r.body.decode())
    assert restarted_kernel['id'] == kernel2['id']
    assert restarted_kernel['name'] == kernel2['name']

    # Start a kernel with a path
    r = await fetch(
        'api', 'kernels',
        method='POST',
                body=json.dumps({
            'name': NATIVE_KERNEL_NAME,
            'path': '/foo'
        })
    )
    kernel3 = json.loads(r.body.decode())
    assert isinstance(kernel3, dict)


async def test_kernel_handler(fetch):
    # Create a kernel
    r = await fetch(
        'api', 'kernels',
        method='POST',
        body=json.dumps({
            'name': 'pyimport/kernel'
        })
    )
    kernel_id = json.loads(r.body.decode())['id']
    r = await fetch(
        'api', 'kernels', kernel_id,
        method='GET'
    )
    kernel = json.loads(r.body.decode())
    assert r.code == 200
    assert isinstance(kernel, dict)
    assert 'id' in kernel
    assert kernel['id'] == kernel_id

    # Requests a bad kernel id.
    bad_id = '111-111-111-111-111'
    with pytest.raises(tornado.httpclient.HTTPClientError) as e:
        r = await fetch(
            'api', 'kernels', bad_id,
            method='GET'
        )
    assert expected_http_error(e, 404)

    # Delete kernel with id.
    r = await fetch(
        'api', 'kernels', kernel_id,
        method='DELETE',
    )
    assert r.code == 204

    # Get list of kernels
    r = await fetch(
        'api', 'kernels',
        method='GET'
    )
    kernel_list = json.loads(r.body.decode())
    assert kernel_list == []

    # Request to delete a non-existent kernel id
    bad_id = '111-111-111-111-111'
    with pytest.raises(tornado.httpclient.HTTPClientError) as e:
        r = await fetch(
            'api', 'kernels', bad_id,
            method='DELETE'
        )
    assert expected_http_error(e, 404, 'Kernel does not exist: ' + bad_id)


async def test_connection(fetch, ws_fetch, http_port, auth_header):
    print('hello')
    # Create kernel
    r = await fetch(
        'api', 'kernels',
        method='POST',
        body=json.dumps({
            'name': 'pyimport/kernel'
        })
    )
    kid = json.loads(r.body.decode())['id']

    # Get kernel info
    r = await fetch(
        'api', 'kernels', kid,
        method='GET'
    )
    model = json.loads(r.body.decode())
    assert model['connections'] == 0

    time.sleep(1)
    # Open a websocket connection.
    ws = await ws_fetch(
        'api', 'kernels', kid, 'channels'
    )

    # Test that it was opened.
    r = await fetch(
        'api', 'kernels', kid,
        method='GET'
    )
    model = json.loads(r.body.decode())
    assert model['connections'] == 1

    # Close websocket
    ws.close()
    # give it some time to close on the other side:
    for i in range(10):
        r = await fetch(
            'api', 'kernels', kid,
            method='GET'
        )
        model = json.loads(r.body.decode())
        if model['connections'] > 0:
            time.sleep(0.1)
        else:
            break

    r = await fetch(
        'api', 'kernels', kid,
        method='GET'
    )
    model = json.loads(r.body.decode())
    assert model['connections'] == 0


async def test_config2(serverapp):
    assert serverapp.kernel_manager.allowed_message_types == []

