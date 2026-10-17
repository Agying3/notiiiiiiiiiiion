"""Launch options for an ordinary installed Edge browser, with no configured proxy."""
import os


def options(output, environ=None):
    env = dict(os.environ if environ is None else environ)
    env = {key: value for key, value in env.items()
           if key.upper() not in {'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY'}}
    return {
        'channel': 'msedge', 'headless': False, 'proxy': None,
        'args': ['--no-proxy-server'], 'env': env, 'viewport': None,
        'record_har_path': str(output / 'full-network.har'),
        'record_har_content': 'embed', 'record_har_mode': 'full',
    }
