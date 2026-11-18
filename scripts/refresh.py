#!/usr/bin/env python3
"""Collect, classify, score, and publish a monthly short-video format index.

Use a data feed licensed to permit derivative rankings and archival storage.
Ordinary YouTube Data API credentials do NOT permit the derived-metric workflow;
the optional YouTube connector requires separately documented approval.
Secrets are server-side only and are never published with the website.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
import json
import logging
import math
import os
from pathlib import Path
import re
import statistics
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SITE_DATA = ROOT / 'site' / 'data'
TAXONOMY_PATH = ROOT / 'scripts' / 'taxonomy.json'
LOGGER = logging.getLogger('format-radar')

# Deliberately sample broad niches; avoid assuming this reflects every video online.
NICHES = [
    ('Comedy', 'funny comedy'), ('Fitness', 'fitness workout'),
    ('Food', 'cooking recipes'), ('Automotive', 'cars motorcycles'),
    ('Beauty', 'makeup skincare'), ('Gaming', 'gaming'),
    ('Technology', 'tech gadgets'), ('Business', 'money business'),
    ('Travel', 'travel places'), ('Pets', 'pets animals'),
    ('Science', 'science facts'), ('Fashion', 'outfit fashion'),
    ('DIY', 'diy crafts'), ('Sports', 'sports highlights'),
    ('Lifestyle', 'lifestyle vlog'), ('Music', 'music performance'),
    ('Art', 'art drawing'), ('Photography', 'photography camera'),
    ('Productivity', 'study productivity'), ('Home', 'home design'),
]
YOUTUBE_API = 'https://www.googleapis.com/youtube/v3/'
OPENAI_API = 'https://api.openai.com/v1/chat/completions'


def request_json(url, params=None, *, payload=None, headers=None):
    """Small stdlib HTTP client with retry; don't log secret-bearing URLs."""
    if params:
        url = url + ('&' if '?' in url else '?') + urlencode(params)
    body = json.dumps(payload).encode('utf-8') if payload is not None else None
    headers = headers or {}
    if payload is not None:
        headers['Content-Type'] = 'application/json'
    for attempt in range(4):
        try:
            req = Request(url, data=body, headers=headers)
            with urlopen(req, timeout=65) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 3:
                # Avoid leaking a key embedded in the request URL.
                msg = exc.read(500).decode('utf-8', errors='replace')
                raise RuntimeError(f'API request failed ({exc.code}): {msg[:350]}') from None
            LOGGER.warning('Transient API status %s; retry %d/3', exc.code, attempt + 1)
        except (URLError, TimeoutError) as exc:
            if attempt == 3:
                raise RuntimeError(f'API connection failed: {type(exc).__name__}') from None
            LOGGER.warning('Transient network issue; retry %d/3', attempt + 1)
        time.sleep(2 ** attempt)
    raise RuntimeError('Request failed')


def month_window(now: datetime, explicit_month: str | None = None):
    """Return UTC first-second window for previous complete calendar month."""
    now = now.astimezone(timezone.utc)
    if explicit_month:
        if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', explicit_month):
            raise ValueError('Month must be YYYY-MM')
        year, month = map(int, explicit_month.split('-'))
    else:
        end_prev = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        year, month = end_prev.year, end_prev.month
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = (datetime(year + 1, 1, 1, tzinfo=timezone.utc) if month == 12
           else datetime(year, month + 1, 1, tzinfo=timezone.utc))
    if end > now:
        raise ValueError('Requested month has not finished yet')
    return start, end


def parse_duration(value: str) -> int:
    """Read YouTube ISO 8601 PT duration; unknown formats return 0."""
    match = re.fullmatch(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', value or '')
    if not match:
        return 0
    h, m, s = match.groups()
    return int(h or 0) * 3600 + int(m or 0) * 60 + int(s or 0)


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def batched(values, chunk_size):
    for offset in range(0, len(values), chunk_size):
        yield values[offset:offset + chunk_size]


def collect_youtube(key: str, start: datetime, end: datetime, *, max_per_channel: int = 5):
    """Fetch broad search sample, dedupe, and get verified public statistics."""
    candidates: dict[str, dict] = {}
    search_calls = 0
    start_iso = start.strftime('%Y-%m-%dT%H:%M:%SZ')
    end_iso = end.strftime('%Y-%m-%dT%H:%M:%SZ')
    for niche, phrase in NICHES:
        for order in ('viewCount', 'date'):
            query = {
                'key': key, 'part': 'snippet', 'type': 'video',
                'videoDuration': 'short', 'maxResults': 50,
                'q': f'#shorts {phrase}', 'order': order,
                'publishedAfter': start_iso, 'publishedBefore': end_iso,
                'safeSearch': 'moderate',
            }
            result = request_json(YOUTUBE_API + 'search', query)
            search_calls += 1
            for item in result.get('items', []):
                video_id = item.get('id', {}).get('videoId')
                if not video_id or not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
                    continue
                snippet = item.get('snippet', {})
                entry = candidates.setdefault(video_id, {
                    'id': video_id, 'title': snippet.get('title', ''),
                    'description': snippet.get('description', ''),
                    'published_at': snippet.get('publishedAt', ''),
                    'channel_id': snippet.get('channelId', ''),
                    'channel': snippet.get('channelTitle', 'Unknown creator'),
                    'niches': set(),
                })
                entry['niches'].add(niche)
    LOGGER.info('Search: %d calls, %d deduplicated candidates', search_calls, len(candidates))
    details: list[dict] = []
    for batch in batched(list(candidates), 50):
        payload = request_json(YOUTUBE_API + 'videos', {
            'key': key, 'part': 'statistics,contentDetails,snippet',
            'id': ','.join(batch), 'maxResults': 50,
        })
        for item in payload.get('items', []):
            vid_id = item.get('id')
            if vid_id not in candidates:
                continue
            original = candidates[vid_id]
            snippet = item.get('snippet', {})
            length = parse_duration(item.get('contentDetails', {}).get('duration', ''))
            # API cannot confirm aspect ratio. Under 181 seconds is only a Shorts candidate.
            if not 8 <= length <= 180:
                continue
            published = snippet.get('publishedAt') or original['published_at']
            try:
                dt = parse_utc(published)
            except (ValueError, AttributeError):
                continue
            if not start <= dt < end:
                continue
            stats = item.get('statistics', {})
            views = int(stats.get('viewCount') or 0)
            if views < 1:
                continue
            details.append({
                'id': vid_id, 'title': snippet.get('title') or original['title'],
                'description': (snippet.get('description') or original['description'])[:650],
                'channel_id': snippet.get('channelId') or original['channel_id'],
                'channel': snippet.get('channelTitle') or original['channel'],
                'published_at': published, 'views': views,
                'likes': int(stats['likeCount']) if 'likeCount' in stats else None,
                'comments': int(stats['commentCount']) if 'commentCount' in stats else None,
                'duration': length, 'niches': sorted(original['niches']),
            })
    details.sort(key=lambda x: x['views'], reverse=True)
    by_channel = Counter()
    balanced = []
    for x in details:
        channel = x['channel_id'] or x['channel']
        if by_channel[channel] >= max_per_channel:
            continue
        by_channel[channel] += 1
        balanced.append(x)
    LOGGER.info('Validated %d <=180s videos; balanced sample contains %d', len(details), len(balanced))
    return balanced, search_calls


def collect_licensed_feed(url: str, token: str | None, start: datetime, end: datetime):
    """Collect records from a properly licensed third-party video data provider.

    See README.md for the stable feed schema. A feed can contain format_id tags
    from its provider. Metadata tagging is opt-in and requires separate rights.
    """
    if not url.startswith('https://'):
        raise RuntimeError('RADAR_FEED_URL must use HTTPS')
    headers = {'Accept': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    # Provider can use start/end as filters or ignore them; we validate locally.
    separator = '&' if '?' in url else '?'
    response = request_json(url + separator + urlencode({
        'start': start.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'end': end.strftime('%Y-%m-%dT%H:%M:%SZ'),
    }), headers=headers)
    raw_videos = response.get('videos')
    if not isinstance(raw_videos, list):
        raise RuntimeError('Licensed feed must contain a videos array')
    feed_name = response.get('source_name') or 'Licensed feed'
    if not isinstance(feed_name, str) or len(feed_name) > 80:
        raise RuntimeError('Invalid feed source_name')
    normal = []
    seen = set()
    for row in raw_videos:
        try:
            platform = str(row.get('platform') or 'Other')[:40]
            video_id = str(row['id'])[:200]
            date = str(row['published_at'])
            if (platform, video_id) in seen:
                continue
            published_at = parse_utc(date)
            if not start <= published_at < end:
                continue
            duration = int(row.get('duration') or 0)
            if duration and not 8 <= duration <= 180:
                continue
            views = int(row.get('views') or 0)
            if views < 1:
                continue
            url_candidate = str(row.get('url') or '')
            if url_candidate and not url_candidate.startswith('https://'):
                url_candidate = ''
            niches = row.get('niches') or ([row['niche']] if row.get('niche') else ['General'])
            if not isinstance(niches, list):
                niches = ['General']
            format_id = str(row.get('format_id') or '')[:80]
            confidence = clamp(float(row.get('confidence') or 0.9)) if format_id else 0
            normal.append({
                'id': f'{platform}:{video_id}', 'external_id': video_id, 'platform': platform, 'url': url_candidate,
                'title': str(row.get('title') or '')[:200],
                'description': str(row.get('description') or '')[:650],
                'channel_id': str(row.get('channel_id') or row.get('channel') or '')[:200],
                'channel': str(row.get('channel') or 'Unknown creator')[:200],
                'published_at': date, 'views': views,
                'likes': max(0, int(row['likes'])) if row.get('likes') is not None else None,
                'comments': max(0, int(row['comments'])) if row.get('comments') is not None else None,
                'duration': duration, 'niches': [str(n)[:50] for n in niches[:10]],
                'format_id': format_id, 'confidence': confidence,
            })
            seen.add((platform, video_id))
        except (ValueError, TypeError, KeyError) as exc:
            LOGGER.debug('Skipped invalid feed record: %s', type(exc).__name__)
    LOGGER.info('Licensed feed %s supplied %d valid records', feed_name, len(normal))
    return normal, feed_name


def classify_keyword(video: dict, taxonomy: list[dict]):
    """Conservative, transparent fallback; metadata-only tagging."""
    title = (video.get('title') or '').lower()
    desc = (video.get('description') or '').lower()[:300]
    matches = []
    for row in taxonomy:
        for keyword in row['keywords']:
            pattern = r'(?<!\w)' + re.escape(keyword.lower()) + r'(?!\w)'
            # Titles are more diagnostic than hashtags buried in a description.
            if re.search(pattern, title):
                matches.append((3 + len(keyword) / 40, row['id'], 0.80))
            elif re.search(pattern, desc):
                matches.append((1 + len(keyword) / 40, row['id'], 0.59))
    if not matches:
        return None
    matches.sort(reverse=True)
    best = matches[0]
    # Description-only matches are weak evidence; exclude rather than fabricate.
    if best[2] < 0.70:
        return None
    return {'format_id': best[1], 'confidence': best[2]}


def classify_with_ai(videos: list[dict], taxonomy: list[dict], key: str):
    """Batch OpenAI title/description tagging; conservative for ambiguous clips."""
    model = os.environ.get('OPENAI_MODEL', 'gpt-4.1-mini')
    choices = '; '.join(f'{row["id"]}: {row["name"]}' for row in taxonomy)
    result: dict[str, dict] = {}
    system = (
        'You classify YouTube video metadata into reusable short-form CONTENT FORMATS. '
        'Return valid JSON with a key "items" containing objects with id, format_id and confidence (0 to 1). '
        'format_id MUST be one of the predefined ids or null. '
        'Only assign a format if the TITLE or DESCRIPTION provides substantial evidence. '
        'Do not guess filming style, edits, audio, or narrative structure from generic titles. '
        'If ambiguous, use null. Confidence at least 0.70 is required to include a video. '
        'No commentary or invented claims. Do not try to rank the videos. '
        'Allowed format ids: ' + choices
    )
    for index, group in enumerate(batched(videos, 45), start=1):
        provided = [{'id': x['id'], 'title': x['title'][:140], 'description': x['description'][:220]}
                    for x in group]
        request = {
            'model': model,
            'temperature': 0,
            'response_format': {'type': 'json_object'},
            'messages': [{'role': 'system', 'content': system},
                         {'role': 'user', 'content': 'Tag these clips. Return {"items":[...]}:\n'+json.dumps(provided, ensure_ascii=False)}],
        }
        try:
            response = request_json(OPENAI_API, payload=request,
                                    headers={'Authorization': 'Bearer ' + key})
            text = response['choices'][0]['message']['content']
            labels = json.loads(text).get('items', [])
            known_ids = {x['id'] for x in group}
            permitted = {row['id'] for row in taxonomy}
            for label in labels:
                video_id,format_id = label.get('id'),label.get('format_id')
                confidence = float(label.get('confidence') or 0)
                if video_id in known_ids and format_id in permitted and confidence >= 0.70:
                    result[video_id] = {'format_id': format_id,
                                        'confidence': min(1, max(0, confidence))}
            LOGGER.info('AI classified batch %d: %d records', index, len(labels))
        except (ValueError, TypeError, KeyError, RuntimeError) as exc:
            LOGGER.warning('AI batch %d unavailable (%s); using conservative keyword fallback',
                           index, type(exc).__name__)
            for video in group:
                label = classify_keyword(video, taxonomy)
                if label:
                    result[video['id']] = label
    return result


def clamp(value, lo=0.0, hi=1.0):
    return max(lo, min(hi, value))


def score_formats(videos: list[dict], taxonomy: list[dict], now: datetime,
                  classifications: dict[str, dict], min_creators: int = 2):
    """Rank only evidenced format clusters using documented proxy signals.

    Score, each 0..1 before weighting:
      38% median views/day, capped at 1m/day
      22% mean (likes + 2 * comments) / views, capped at 8%
      25% independent creators, capped at 20
      15% sampled niche breadth, capped at 8
    """
    groups = defaultdict(list)
    id_to_taxonomy = {x['id']: x for x in taxonomy}
    for video in videos:
        assigned = classifications.get(video['id'])
        if not assigned or assigned['format_id'] not in id_to_taxonomy:
            continue
        x = dict(video)
        age = max(1.0, (now - parse_utc(x['published_at'])).total_seconds() / 86400)
        x['views_per_day'] = x['views'] / age
        if x['likes'] is not None or x['comments'] is not None:
            engagement = ((x['likes'] or 0) + 2 * (x['comments'] or 0)) / x['views']
            x['engagement'] = clamp(engagement, 0, 0.5)
        else:
            x['engagement'] = None
        x['confidence'] = assigned['confidence']
        groups[assigned['format_id']].append(x)
    result = []
    for format_id, group in groups.items():
        creators = len({(x.get('platform', 'YouTube'), x['channel_id'] or x['channel']) for x in group})
        if creators < min_creators:
            continue
        sample_views = sum(x['views'] for x in group)
        speeds = [x['views_per_day'] for x in group]
        engagement_values = [x['engagement'] for x in group if x['engagement'] is not None]
        eng = statistics.mean(engagement_values) if engagement_values else 0
        niches = Counter(n for x in group for n in x['niches'])
        vel_score = clamp(math.log10(1 + statistics.median(speeds)) / 6)
        eng_score = clamp(eng / 0.08)
        creator_score = clamp(math.log1p(creators) / math.log1p(20))
        breadth_score = clamp(len(niches) / 8)
        score = round(100 * (0.38 * vel_score + 0.22 * eng_score +
                             0.25 * creator_score + 0.15 * breadth_score), 1)
        seen_creators = set()
        examples = []
        for video in sorted(group, key=lambda x: x['views_per_day'], reverse=True):
            channel = (video.get('platform', 'YouTube'), video['channel_id'] or video['channel'])
            if channel in seen_creators:
                continue
            seen_creators.add(channel)
            examples.append({'id': video.get('external_id', video['id']), 'title': video['title'],
                             'platform': video.get('platform', 'YouTube'),
                             'url': video.get('url', ''),
                             'channel': video['channel'], 'views': video['views'],
                             'published_at': video['published_at']})
            if len(examples) == 5:
                break
        taxonomy_row = id_to_taxonomy[format_id].copy()
        taxonomy_row.pop('keywords', None)
        result.append(dict(taxonomy_row, rank=None, score=score,
                           confidence=round(statistics.mean(x['confidence'] for x in group), 2),
                           niche=niches.most_common(1)[0][0] if niches else 'Uncategorized',
                           niches=[x[0] for x in niches.most_common()],
                           stats={'videos': len(group), 'creators': creators, 'views': sample_views,
                                  'avg_views': round(sample_views / len(group)),
                                  'engagement_pct': round(eng * 100, 2),
                                  'views_per_day': round(statistics.median(speeds))},
                           sample_videos=examples))
    result.sort(key=lambda x: (-x['score'], -x['stats']['creators'], -x['stats']['views'], x['name']))
    for rank, item in enumerate(result[:50], start=1):
        item['rank'] = rank
    return result[:50]


def write_atomic(path: Path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(content, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def save_issue(issue: dict, data_dir: Path):
    """Add a versioned archive and latest marker only after all checks pass."""
    index_path = data_dir / 'index.json'
    manifest = json.loads(index_path.read_text()) if index_path.exists() else {'latest':None,'snapshots':[]}
    item = {'month': issue['month'], 'period_label': issue['period_label'],
            'generated_at': issue['generated_at'], 'count': len(issue['results'])}
    old = [s for s in manifest.get('snapshots', []) if s.get('month') != issue['month']]
    manifest['snapshots'] = [item, *old]
    manifest['snapshots'].sort(key=lambda x:x['month'], reverse=True)
    manifest['latest'] = manifest['snapshots'][0]['month']
    write_atomic(data_dir / 'archive' / (issue['month']+'.json'), issue)
    if manifest['latest'] == issue['month']:
        write_atomic(data_dir / 'latest.json', issue)
    write_atomic(index_path, manifest)


def run(args):
    taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding='utf-8'))
    now = datetime.now(timezone.utc)
    start, end = month_window(now, args.month)
    month = start.strftime('%Y-%m')
    LOGGER.info('Collecting calendar month %s (%s to %s UTC)', month, start, end)
    feed_name = None
    licensed_url = os.environ.get('RADAR_FEED_URL')
    if args.fixture:
        raw = json.loads(Path(args.fixture).read_text())
        videos = raw['videos']
        queries = raw.get('query_count', 0)
        feed_name = raw.get('source_name', 'Fixture')
        LOGGER.info('Fixture mode: %d records (never deploy as live)', len(videos))
    elif licensed_url:
        if os.environ.get('RADAR_DATA_RIGHTS_CONFIRMED') != 'true':
            raise RuntimeError('Set RADAR_DATA_RIGHTS_CONFIRMED=true only after confirming derivative rankings, republishing examples, and archival data are permitted by your provider agreement.')
        videos, feed_name = collect_licensed_feed(
            licensed_url, os.environ.get('RADAR_FEED_TOKEN'), start, end)
        queries = 0
    else:
        if os.environ.get('YOUTUBE_DERIVED_METRICS_APPROVED') != 'true':
            raise RuntimeError('Requires an authorized RADAR_FEED_URL, or documented YouTube approval for derived metrics and retention before enabling the YouTube connector. Ordinary YouTube API keys alone are insufficient.')
        if os.environ.get('RADAR_DATA_RIGHTS_CONFIRMED') != 'true':
            raise RuntimeError('Rights confirmation required for archival ranking workflow.')
        key = os.environ.get('YOUTUBE_API_KEY')
        if not key:
            raise RuntimeError('Approved YouTube connector needs YOUTUBE_API_KEY')
        videos, queries = collect_youtube(key, start, end)
        for video in videos:
            video['platform'] = 'YouTube'
        feed_name = 'YouTube (approved analytics use)'
    if len(videos) < args.min_videos:
        raise RuntimeError(f'Insufficient videos: {len(videos)} < {args.min_videos}. Previous issue preserved.')
    allowed_ids = {row['id'] for row in taxonomy}
    assignments = {
        x['id']: {'format_id': x['format_id'], 'confidence': float(x.get('confidence') or 0.9)}
        for x in videos if x.get('format_id') in allowed_ids
    }
    untagged = [x for x in videos if x['id'] not in assignments]
    if os.environ.get('RADAR_ALLOW_METADATA_TAGGING') == 'true' or args.fixture:
        ai_key = os.environ.get('OPENAI_API_KEY')
        if ai_key and not args.no_ai:
            assignments.update(classify_with_ai(untagged, taxonomy, ai_key))
        else:
            assignments.update({x['id']:label for x in untagged
                                if (label:=classify_keyword(x, taxonomy))})
    LOGGER.info('Metadata/approved feed labels: %d/%d', len(assignments), len(videos))
    results = score_formats(videos, taxonomy, now, assignments, min_creators=args.min_creators)
    if len(results) < args.min_formats:
        raise RuntimeError(f'Insufficient evidenced formats: {len(results)} < {args.min_formats}. Previous issue preserved.')
    issue = {
        'schema_version': 1,
        'mode': 'fixture' if args.fixture else 'live',
        'month': month,
        'period_label': start.strftime('%B %Y'),
        'generated_at': now.isoformat(timespec='seconds').replace('+00:00','Z'),
        'window_start': start.isoformat(timespec='seconds').replace('+00:00','Z'),
        'window_end': end.isoformat(timespec='seconds').replace('+00:00','Z'),
        'platforms': sorted({x.get('platform', 'YouTube') for x in videos}),
        'source_name': feed_name,
        'sample_size': len(videos),
        'query_count': queries,
        'niches_covered': len({n for x in videos for n in x['niches']}),
        'note': 'Independent sample-based ranking from a licensed data feed or specially approved API use; not an official platform leaderboard. Observed views and a velocity proxy are different from actual view growth.',
        'results': results,
    }
    LOGGER.info('Ranked %d formats. Top 5: %s', len(results),
                ', '.join(x['name'] for x in results[:5]))
    if args.dry_run or args.fixture:
        LOGGER.info('Dry run/fixture: no production JSON written')
    else:
        save_issue(issue, Path(args.output))
        LOGGER.info('Saved %s and archive to %s', month, args.output)
    return issue


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--month', help='Completed calendar month YYYY-MM; default is previous month')
    parser.add_argument('--output', default=str(SITE_DATA))
    parser.add_argument('--fixture', help='Offline test JSON; never writes production files')
    parser.add_argument('--dry-run', action='store_true', help='Collect and score without writing')
    parser.add_argument('--no-ai', action='store_true', help='Use deterministic keyword classification only')
    parser.add_argument('--min-videos', type=int, default=30)
    parser.add_argument('--min-formats', type=int, default=3)
    parser.add_argument('--min-creators', type=int, default=2)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    try:
        run(args)
    except (RuntimeError, ValueError) as exc:
        LOGGER.error('%s', exc)
        sys.exit(1)


if __name__ == '__main__':
    main()
