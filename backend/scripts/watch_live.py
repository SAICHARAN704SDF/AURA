"""Watch real AURA backend events over HTTP using only Python's standard library.

Start the website server separately, then upload a document or submit a prompt.
No model calls or database writes are made by this monitor. Detailed events are
bounded by the server's in-memory buffer; this is not a durable audit exporter.
"""
import argparse
from datetime import datetime
import json
import time
from urllib.error import URLError
from urllib.request import urlopen


DETAILS = ('event_type', 'task_id', 'tool', 'workflow_state', 'provider', 'model',
           'chunks', 'pages', 'documents', 'hits', 'misses', 'dimensions', 'tokens',
           'http_status', 'duration_ms', 'error', 'source', 'retry_after_seconds')


def read_events(base, after):
    """Read the existing sanitized event feed; never invoke an agent or model."""
    with urlopen(f'{base.rstrip("/")}/monitor/events?after={after}', timeout=5) as response:
        return json.load(response)


def show(event):
    """Display correlation IDs and selected operational metadata, not prompts."""
    stamp = datetime.fromtimestamp(event['time']).strftime('%H:%M:%S')
    detail = ' '.join(f'{key}={json.dumps(event[key], ensure_ascii=True)}'
                      for key in DETAILS if key in event)
    print(f"{stamp} [{event.get('trace_id', '')}] "
          f"{event.get('stage', '?')} -> {event.get('status', 'info')} {detail}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--trace', help='Only display this trace/workflow ID')
    parser.add_argument('--history', action='store_true', help='Include events already in the server buffer')
    parser.add_argument('--once', action='store_true', help='Read the current buffer once and exit')
    args = parser.parse_args()
    cursor = 0
    initialized = False
    disconnected = False
    print(f'Watching {args.url} — real events only. Start an operation in the website. Ctrl+C stops.', flush=True)
    try:
        while True:
            try:
                data = read_events(args.url, cursor)
                if disconnected:
                    print('Reconnected.', flush=True)
                    disconnected = False
                if data['cursor'] < cursor:
                    print('Server event buffer reset; restarting cursor.', flush=True)
                    cursor = 0
                    continue
                if data.get('truncated'):
                    print('Older events expired from the server buffer.', flush=True)
                if initialized or args.history or args.once:
                    for event in data['events']:
                        if not args.trace or args.trace in (event.get('trace_id'), event.get('workflow_id')):
                            show(event)
                cursor = data['cursor']
                initialized = True
                if args.once:
                    return
            except (URLError, OSError, ValueError, KeyError) as exc:
                if args.once:
                    parser.exit(1, f'Cannot read AURA events ({type(exc).__name__}). Start the server or check --url.\n')
                if not disconnected:
                    print('Cannot reach the event feed. Start AURA; reconnecting automatically.', flush=True)
                    disconnected = True
            time.sleep(0.7)
    except KeyboardInterrupt:
        print('\nMonitor stopped. AURA continues running.')


if __name__ == '__main__':
    main()
