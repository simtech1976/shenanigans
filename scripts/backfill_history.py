#!/usr/bin/env python3
"""Record past versions from CHANGELOG.md in GitHub as completed work.

For each released version in CHANGELOG.md (oldest first), this:
  * creates a milestone (e.g. "v0.6.0") and closes it,
  * creates a closed issue labelled "history" with that version's changelog
    section as its description,
  * adds the issue to your GitHub Project with Status set to Done.

If a version heading has a date, e.g. "## [0.9.0] - 2026-10-01", it is used as
the milestone's due date and to fill a "Completed on" date field in the project
(created if missing). Add approximate dates to the headings first if you want
the roadmap to show them.

Safe to run more than once: existing milestones and issues are reused.

Setup (first time only):  gh auth login   and   gh auth refresh -s project
Find the project number:  gh project list --owner "@me"
Usage (from the repository folder):
    python3 scripts/backfill_history.py 3 --dry-run     # preview, changes nothing
    python3 scripts/backfill_history.py 3               # do it
    python3 scripts/backfill_history.py 3 --owner my-org
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# Issue and milestone titles for each past version
SUMMARIES = {
    '0.1.0': 'Streamlit and Supabase foundation, email sign-in',
    '0.2.0': 'Core database and security rules',
    '0.3.0': 'D6 dice system',
    '0.4.0': 'Games, notes, abilities and cover images',
    '0.5.0': 'Skill points, upgrades and activity log',
    '0.6.0': 'Stats & skills tab, skills as bonuses',
    '0.7.0': 'Game rules moved to Python, D20, single setup script',
    '0.8.0': 'Icons and database reset script',
    '0.9.0': 'Players, profiles, Microsoft/Discord sign-in, password reset',
}
LABEL = 'history'
DATE_FIELD = 'Completed on'
HEADING = re.compile(r'^## \[(\d+\.\d+\.\d+)\](?:\s*-\s*(\d{4}-\d{2}-\d{2}))?\s*$')

DRY_RUN = False


def gh(*args, stdin=None, as_json=False, mutating=False):
    """Run a GitHub CLI command. Mutating commands are only printed in dry-run mode."""
    if mutating and DRY_RUN:
        print('    [dry run] gh ' + ' '.join(a if ' ' not in a else repr(a) for a in args))
        return {} if as_json else ''
    res = subprocess.run(['gh', *args], input=stdin, text=True, capture_output=True)
    if res.returncode != 0:
        sys.exit(f"\nCommand failed: gh {' '.join(args)}\n{res.stderr.strip()}")
    out = res.stdout.strip()
    return json.loads(out) if as_json else out


def parse_changelog(path: Path) -> list[dict]:
    """Released versions (not Unreleased), oldest first, with date and section text."""
    versions, current = [], None
    for line in path.read_text(encoding='utf-8').splitlines():
        match = HEADING.match(line)
        if match:
            current = {'version': match.group(1), 'date': match.group(2), 'lines': []}
            versions.append(current)
        elif line.startswith('## ') or re.match(r'^\[[^\]]+\]:\s', line):
            current = None   # Unreleased section, or the link list at the bottom
        elif current is not None:
            current['lines'].append(line)
    for v in versions:
        v['body'] = '\n'.join(v.pop('lines')).strip()
    return sorted(versions, key=lambda v: tuple(int(n) for n in v['version'].split('.')))


def main():
    global DRY_RUN
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('project', help='project number (from: gh project list --owner "@me")')
    parser.add_argument('--owner', default='@me', help='project owner: "@me" (default) or an organisation')
    parser.add_argument('--dry-run', action='store_true', help='show what would happen, change nothing')
    parser.add_argument('--changelog', default='CHANGELOG.md')
    args = parser.parse_args()
    DRY_RUN = args.dry_run

    versions = [v for v in parse_changelog(Path(args.changelog)) if v['version'] in SUMMARIES]
    if not versions:
        sys.exit('No matching versions found in the changelog.')
    print(f"{'DRY RUN: ' if DRY_RUN else ''}Recording {len(versions)} past versions "
          f"({versions[0]['version']} to {versions[-1]['version']}).\n")

    # ---------- what already exists ----------
    milestones = {}
    for line in gh('api', 'repos/{owner}/{repo}/milestones?state=all&per_page=100', '--paginate',
                   '--jq', '.[] | [.title, (.number|tostring)] | @tsv').splitlines():
        title, number = line.split('\t')
        milestones[title] = number
    issues = {i['title']: i['url'] for i in
              gh('issue', 'list', '--state', 'all', '--limit', '1000', '--json', 'title,url', as_json=True)}

    project_id = gh('project', 'view', args.project, '--owner', args.owner, '--format', 'json',
                    as_json=True)['id']

    def project_fields():
        return gh('project', 'field-list', args.project, '--owner', args.owner, '--limit', '100',
                  '--format', 'json', as_json=True)['fields']

    fields = project_fields()
    status = next((f for f in fields if f['name'] == 'Status'), None)
    done = next((o for o in (status or {}).get('options', []) if o['name'] == 'Done'), None)
    if not status or not done:
        sys.exit('The project needs a "Status" field with a "Done" option (the Iterative '
                 'development template has one).')

    date_field = next((f for f in fields if f['name'] == DATE_FIELD), None)
    if any(v['date'] for v in versions) and not date_field:
        print(f'Creating the "{DATE_FIELD}" date field in the project...')
        gh('project', 'field-create', args.project, '--owner', args.owner, '--name', DATE_FIELD,
           '--data-type', 'DATE', mutating=True)
        if not DRY_RUN:
            date_field = next((f for f in project_fields() if f['name'] == DATE_FIELD), None)

    gh('label', 'create', LABEL, '--color', 'c5def5',
       '--description', 'Past work recorded retrospectively', '--force', mutating=True)

    # ---------- each version ----------
    for v in versions:
        version, date = v['version'], v['date']
        milestone = f'v{version}'
        title = f'{milestone}: {SUMMARIES[version]}'
        print(f"{title}{f'  ({date})' if date else ''}")

        # Milestone: create (or reopen) so the issue can be assigned to it
        if milestone in milestones:
            number = milestones[milestone]
            gh('api', '-X', 'PATCH', f'repos/{{owner}}/{{repo}}/milestones/{number}',
               '-f', 'state=open', mutating=True)
            print('  = milestone exists')
        else:
            fields_args = ['-f', f'title={milestone}', '-f', f'description={SUMMARIES[version]}']
            if date:
                fields_args += ['-f', f'due_on={date}T12:00:00Z']
            number = gh('api', 'repos/{owner}/{repo}/milestones', *fields_args,
                        '--jq', '.number|tostring', mutating=True) or '?'
            print('  + milestone created')

        # Issue: create and close
        if title in issues:
            url = issues[title]
            print('  = issue exists')
        else:
            body = (f"{v['body']}\n\n---\n*Recorded retrospectively from "
                    f"[CHANGELOG.md](../blob/main/CHANGELOG.md).*")
            url = gh('issue', 'create', '--title', title, '--body-file', '-', '--label', LABEL,
                     '--milestone', milestone, stdin=body, mutating=True).splitlines()[-1:] or ['']
            url = url[0]
            if url:
                gh('issue', 'close', url, '--reason', 'completed', mutating=True)
            print('  + issue created and closed')

        # Close the milestone again
        if number != '?':
            gh('api', '-X', 'PATCH', f'repos/{{owner}}/{{repo}}/milestones/{number}',
               '-f', 'state=closed', mutating=True)

        # Project: add with Status Done (and the date, if known)
        if url:
            item = gh('project', 'item-add', args.project, '--owner', args.owner, '--url', url,
                      '--format', 'json', as_json=True, mutating=True)
            item_id = item.get('id')
            if item_id:
                gh('project', 'item-edit', '--id', item_id, '--project-id', project_id,
                   '--field-id', status['id'], '--single-select-option-id', done['id'], mutating=True)
                if date and date_field:
                    gh('project', 'item-edit', '--id', item_id, '--project-id', project_id,
                       '--field-id', date_field['id'], '--date', date, mutating=True)
            print('  + in project as Done')
        elif DRY_RUN:
            print('  + would be added to the project as Done')

    print('\nDone.' if not DRY_RUN else '\nDry run complete: nothing was changed.')


if __name__ == '__main__':
    main()
