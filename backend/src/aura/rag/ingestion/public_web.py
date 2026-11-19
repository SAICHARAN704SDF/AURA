"""Fetch public HTTPS sources with DNS pinning, redirect checks and robots policy."""
import http.client
import ipaddress
import re
import socket
import ssl
import time
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

from aura.core import ServiceError

AGENT = "ResearchOS/1.0"
MAX_BYTES = 5 * 1024 * 1024
ARXIV = re.compile(r"(?:\d{4}\.\d{4,5}|[a-z-]+/\d{7})(?:v\d+)?", re.I)


def target(url):
    try:
        parts = urlsplit(url)
        if (parts.scheme != 'https' or not parts.hostname or parts.username is not None
                or parts.password is not None or parts.port not in (None, 443)
                or any(ord(c) < 33 or c == '\\' for c in url)):
            raise ValueError
        addresses = socket.getaddrinfo(parts.hostname, 443, type=socket.SOCK_STREAM)
        if not addresses:
            raise ValueError
        for entry in addresses:
            address = ipaddress.ip_address(entry[4][0])
            if not address.is_global or address.is_multicast or address.is_reserved:
                raise ValueError
        return parts, addresses[0][4][0]
    except (ValueError, OSError):
        raise ServiceError('invalid_public_url') from None


def request(url, limit, deadline):
    parts, ip = target(url)
    connection = http.client.HTTPSConnection(parts.hostname, timeout=6, context=ssl.create_default_context())
    # Connect to the validated address and authenticate the original hostname with TLS.
    try:
        with socket.create_connection((ip, 443), timeout=6) as sock:
            connection.sock = ssl.create_default_context().wrap_socket(sock, server_hostname=parts.hostname)
            path = parts.path or '/'
            connection.request('GET', path + ('?' + parts.query if parts.query else ''),
                               headers={'User-Agent': AGENT, 'Accept-Encoding': 'identity'})
            response = connection.getresponse()
            body = bytearray()
            while True:
                if time.monotonic() > deadline:
                    raise ServiceError('source_timeout')
                part = response.read1(min(65536, limit + 1 - len(body)))
                body.extend(part)
                if len(body) > limit:
                    raise ServiceError('source_size_limit')
                if not part:
                    break
            return response.status, response.headers, bytes(body)
    except (OSError, ValueError, http.client.HTTPException):
        raise ServiceError('source_unavailable') from None
    finally:
        connection.close()


def fetch(source):
    identifier = source.removeprefix('arXiv:')
    url = 'https://arxiv.org/pdf/' + identifier if ARXIV.fullmatch(identifier) else source
    if match := re.fullmatch(r'https://arxiv\.org/abs/(.+)', url):
        if ARXIV.fullmatch(match[1]):
            url = 'https://arxiv.org/pdf/' + match[1]
    deadline = time.monotonic() + 30
    for _ in range(4):
        parts, _ = target(url)
        status, _, rules = request(f'https://{parts.netloc}/robots.txt', 512_000, deadline)
        if status == 200:
            robots = RobotFileParser()
            robots.parse(rules.decode('utf-8', 'replace').splitlines())
            if not robots.can_fetch(AGENT, url):
                raise ServiceError('source_disallowed')
        elif status not in (404, 410):
            raise ServiceError('source_policy_unavailable')
        status, headers, data = request(url, MAX_BYTES, deadline)
        if status in (301, 302, 303, 307, 308) and headers.get('Location'):
            url = urljoin(url, headers['Location'])
            continue
        if status != 200:
            raise ServiceError('source_unavailable')
        mime = headers.get_content_type()
        suffix = {'application/pdf':'.pdf','text/html':'.html','text/plain':'.txt','text/markdown':'.md'}.get(mime)
        if not suffix:
            raise ServiceError('unsupported_file_type')
        stem = PurePosixPath(parts.path).stem or parts.hostname
        name = re.sub(r'[^\w.-]', '_', stem)[:100] + suffix
        return name, data, url
    raise ServiceError('source_redirect_limit')
