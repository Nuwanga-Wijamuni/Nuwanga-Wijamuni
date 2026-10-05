#!/usr/bin/env python3
"""Refresh the dated GitHub profile activity graphics using public GitHub data.

Run from any directory: python3 tools/update_activity.py
Only Python's standard library is required. No credentials are read or stored.
"""
import argparse
import datetime as dt
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.request

USER = 'Nuwanga-Wijamuni'
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'


class Calendar(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells, self.tips = {}, {}
        self.tip, self.buffer = None, ''

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('data-date'):
            self.cells[a['id']] = {'date': a['data-date'], 'level': int(a['data-level'])}
        if tag == 'tool-tip':
            self.tip, self.buffer = a.get('for'), ''

    def handle_data(self, text):
        if self.tip:
            self.buffer += text

    def handle_endtag(self, tag):
        if tag == 'tool-tip' and self.tip:
            self.tips[self.tip], self.tip = self.buffer.strip(), None

    def values(self):
        result = []
        for key, cell in self.cells.items():
            tip = self.tips.get(key, '')
            match = re.search(r'([\d,]+) contribution', tip)
            if tip.startswith('No contributions'):
                count = 0
            elif match:
                count = int(match.group(1).replace(',', ''))
            else:
                raise ValueError('GitHub contribution markup changed; refusing to invent counts.')
            result.append(dict(cell, count=count))
        if not result:
            raise ValueError('No contribution calendar was returned.')
        return result


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'Nuwanga-GitHub-Profile', 'Accept': '*/*'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode('utf-8')


def text(x, y, value, size=14, color='#a9b8c3', weight=400, anchor='start'):
    return f'<text x="{x}" y="{y}" font-family="Arial,Helvetica,sans-serif" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{html.escape(str(value))}</text>'


def canvas(height, title):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="{height}" viewBox="0 0 1120 {height}" role="img"><title>{html.escape(title)}</title>', f'<rect x="1" y="1" width="1118" height="{height-2}" rx="18" fill="#0d141c" stroke="#2d3a45"/>']


def write_svg(name, parts):
    (ASSETS / name).write_text('\n'.join(parts + ['</svg>']), encoding='utf-8')


def render(data):
    today = dt.date.fromisoformat(data['as_of'])
    start = dt.date.fromisoformat(data['range_start'])
    days = data['days']
    total = sum(d['count'] for d in days)
    summary = canvas(144, f'GitHub snapshot for {USER}, {today.isoformat()}')
    for x, value, label, detail in [(30, data['public_repos'], 'PUBLIC REPOSITORIES', 'GitHub profile'), (392, total, 'PROFILE CONTRIBUTIONS', 'Trailing 365 days'), (754, today.strftime('%d %b').upper(), 'ACTIVITY SNAPSHOT', str(today.year))]:
        summary += [text(x, 32, label, 11, '#83969e', 700), text(x, 88, value, 42, '#e8f2e2', 700), text(x, 117, detail, 13)]
    summary += ['<path d="M360 28V117 M722 28V117" stroke="#293742"/>']
    write_svg('github-overview.svg', summary)

    graph = canvas(274, f'GitHub contributions from {start} to {today}: {total}. Contributions include commits and other activity.')
    graph += [text(30, 35, 'CONTRIBUTION ACTIVITY', 15, '#e4edf2', 700), text(1090, 35, f'{start:%d %b %Y} — {today:%d %b %Y}', 12, '#a9b8c3', anchor='end')]
    first_sunday = start - dt.timedelta(days=(start.weekday() + 1) % 7)
    months = set()
    colors = ['#17232d', '#244a28', '#3f7430', '#76b900', '#b1e866']
    for entry in days:
        date = dt.date.fromisoformat(entry['date'])
        week = (date - first_sunday).days // 7
        row = (date.weekday() + 1) % 7
        x, y = 54 + week * 19, 78 + row * 19
        month = (date.year, date.month)
        if month not in months:
            graph += [text(x, 64, date.strftime('%b'), 10)]
            months.add(month)
        count = entry['count']
        intensity = 0 if count == 0 else 1 if count <= 2 else 2 if count <= 5 else 3 if count <= 10 else 4
        graph += [f'<rect x="{x}" y="{y}" width="14" height="14" rx="3" fill="{colors[intensity]}"><title>{date}: {entry["count"]} contributions</title></rect>']
    graph += [text(22, 108, 'M', 10), text(22, 146, 'W', 10), text(22, 184, 'F', 10), text(30, 244, 'GitHub profile activity · contributions include commits, issues, pull requests, and other qualifying activity.', 11)]
    graph += [text(912, 244, 'Less', 10)]
    for i, color in enumerate(colors):
        graph += [f'<rect x="{945+i*19}" y="233" width="13" height="13" rx="3" fill="{color}"/>']
    graph += [text(1049, 244, 'More', 10)]
    write_svg('contribution-activity.svg', graph)

    commits = data['recent_commits'][:4]
    panel = canvas(128 + 86 * len(commits), 'Recent indexed public GitHub commits by Nuwanga Wijamuni')
    panel += [text(30, 35, 'RECENT PUBLIC COMMITS', 15, '#e4edf2', 700), text(1090, 35, f'As of {today:%d %b %Y}', 12, anchor='end')]
    if commits:
        panel += [f'<path d="M51 80 V{80+86*(len(commits)-1)}" stroke="#405d36" stroke-width="2"/>']
    for i, item in enumerate(commits):
        y = 80 + i * 86
        date = dt.datetime.fromisoformat(item['date']).astimezone(dt.timezone(dt.timedelta(hours=5, minutes=30))).date()
        message = item['message'].splitlines()[0]
        if len(message) > 82:
            message = message[:79] + '…'
        panel += [f'<circle cx="51" cy="{y}" r="7" fill="#0d141c" stroke="#a3df42" stroke-width="2"/>', text(75, y+5, item['repo'], 17, '#e6eef3', 700), text(1058, y+5, date.strftime('%d %b %Y'), 12, anchor='end'), text(75, y+30, message, 14), text(75, y+50, item['sha'][:7], 11, '#a3df42')]
    panel += [text(30, 103 + 86 * len(commits), 'Source: GitHub public commit search · newest indexed commits; private activity is excluded.', 11)]
    write_svg('recent-commits.svg', panel)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cached-inputs', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--as-of', type=dt.date.fromisoformat, help=argparse.SUPPRESS)
    args = parser.parse_args()
    today = args.as_of or dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).date()
    start = today - dt.timedelta(days=364)
    collected = {}
    for year in sorted({start.year, today.year}):
        if args.cached_inputs:
            filename = 'contributions.html' if year == today.year else f'contributions-{year}.html'
            source = (args.cached_inputs / filename).read_text()
        else:
            source = fetch(f'https://github.com/users/{USER}/contributions?from={year}-01-01&to={year}-12-31')
        calendar = Calendar()
        calendar.feed(source)
        collected.update({d['date']: d for d in calendar.values()})
    days = [collected[(start + dt.timedelta(days=i)).isoformat()] for i in range(365)]
    if args.cached_inputs:
        profile = json.loads((args.cached_inputs / 'profile.json').read_text())
        commits = json.loads((args.cached_inputs / 'commits.json').read_text())
    else:
        profile = json.loads(fetch(f'https://api.github.com/users/{USER}'))
        commits = json.loads(fetch(f'https://api.github.com/search/commits?q=author%3A{USER}&sort=author-date&order=desc&per_page=6'))
    if commits.get('incomplete_results'):
        raise ValueError('GitHub returned incomplete commit results. Retry later.')
    latest = [{'sha': c['sha'], 'repo': c['repository']['name'], 'message': c['commit']['message'].splitlines()[0], 'date': c['commit']['author']['date'], 'url': c['html_url']} for c in commits['items'][:4]]
    data = {'username': USER, 'as_of': today.isoformat(), 'range_start': start.isoformat(), 'public_repos': profile['public_repos'], 'days': sorted(days, key=lambda x: x['date']), 'recent_commits': latest}
    ASSETS.mkdir(exist_ok=True)
    render(data)
    (ASSETS / 'activity-data.json').write_text(json.dumps(data, indent=2) + '\n')
    print(f'Refreshed 3 activity graphics: {len(days)} days, {sum(d["count"] for d in days)} contributions, {len(latest)} public commits. Snapshot: {today}.')


if __name__ == '__main__':
    main()
