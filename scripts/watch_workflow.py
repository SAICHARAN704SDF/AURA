"""Tail an AURA workflow from a separate terminal."""
import argparse
import time
from pathlib import Path

from aura.orchestration.workflow.persistence import Memory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('workflow_id')
    parser.add_argument('--project', default='aura_papers')
    parser.add_argument('--data-dir', default='data')
    args = parser.parse_args()
    memory = Memory(Path(args.data_dir) / 'workflows.sqlite')
    after = 0
    try:
        while True:
            for event in memory.events(args.workflow_id, args.project, after):
                after = event['sequence']
                details = ' '.join(f'{key}={value}' for key, value in event.items() if key not in ('sequence', 'time', 'state', 'type'))
                print(f"[{after:03d}] {event['state']:<10} {event['type']:<18} {details}", flush=True)
            workflow = memory.get(args.workflow_id, args.project)
            if workflow['state'] in ('COMPLETED', 'FAILED', 'CANCELLED'):
                print(f"FINAL {workflow['state']} error={workflow['error']} llm_calls={workflow['llm_calls']} tool_calls={workflow['tool_calls']}")
                break
            time.sleep(0.5)
    finally:
        memory.close()


if __name__ == '__main__':
    main()
