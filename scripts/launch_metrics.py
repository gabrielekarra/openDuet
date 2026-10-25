"""Snapshot public repository counters; these are not installs or active users."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Create a new JSON snapshot; never overwrite one')
    args = parser.parse_args()
    if not shutil.which('gh'):
        parser.exit(1, 'The GitHub CLI (gh) is required.\n')
    response = subprocess.run(
        ['gh', 'api', 'repos/gabrielekarra/openDuet'], capture_output=True, text=True
    )
    if response.returncode:
        parser.exit(1, 'GitHub metadata request failed; check normal gh access to this repository.\n')
    repo = json.loads(response.stdout)
    snapshot = {
        'captured_at': datetime.now(UTC).isoformat(),
        'repository': repo['full_name'],
        'source': 'https://api.github.com/repos/gabrielekarra/openDuet',
        'stars': repo['stargazers_count'],
        'forks': repo['forks_count'],
        'open_issues': repo['open_issues_count'],
        'subscribers': repo.get('subscribers_count'),
        'installs': None,
        'activated_users': None,
        'qualified_visits': None,
        'note': 'Repository counters only. Usage and campaign attribution require separate evidence.',
    }
    encoded = json.dumps(snapshot, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x') as destination:
            destination.write(encoded)
        print(f'Saved {args.output}')
    else:
        print(encoded, end='')


if __name__ == '__main__':
    main()
