# Format Radar

A responsive, static website plus a scheduled data pipeline for discovering and ranking **up to 50 short-form content formats** every month. The included 50-format library is a **clearly labeled, unranked demonstration**, not fabricated platform analytics.

**What ships**

- A production-deployable, no-build `site/` for GitHub Pages (desktop + mobile).
- 50 example playbooks: hook, shot/content structure, why it works, an adaptation idea.
- Search, category and niche filters, sorting, saved formats (local browser storage), JSON export, source-video breakdowns and month selection.
- Automated job scheduled for **09:17 UTC on the 2nd of each month**. It analyzes the *previous completed calendar month*, commits a dated archive and publishes the updated site.
- A Python standard-library collector and scorer with data validation, automatic retries and failure safeguards. A failed refresh does **not** overwrite the last valid issue.
- No frontend API keys or paid frontend dependencies.

## 1. Preview it locally

From the project folder:

```bash
python -m http.server 8000 --directory site
```

Open http://localhost:8000. Or open the separate `format-radar-preview.html` that was provided alongside this project; it embeds the starter library and needs no server.

## 2. Deploy the website to GitHub Pages

1. Create a GitHub repository (for example `format-radar`) and upload the contents of this project, **including the `.github` folder**, to its default `main` branch.
2. On GitHub, go to **Settings → Pages → Build and deployment → Source → GitHub Actions**.
3. Open **Actions → Monthly Format Radar + Pages** and run the workflow manually with **`refresh_data = false`** for the first publication. This publishes the demo immediately without API credentials.
4. GitHub will provide a live site URL at a path like `https://YOUR-USERNAME.github.io/format-radar/`.

The site itself is fully static. No database, server, or domain purchase is needed to serve existing issues.

## 3. Connect a licensed video-data feed

Real automatic rankings require actual video data **and permission to calculate derived scores, republish linked examples and retain monthly archives**. Ordinary YouTube Data API access alone does not permit this use case; see the section on API rules below.

The easiest v1 integration is an HTTPS endpoint that returns one JSON object with a `videos` array containing records across the niches/platforms covered by your authorized provider. Configure the following in the GitHub repository:

- **Settings → Secrets and variables → Actions → Secrets**: `RADAR_FEED_URL`, and `RADAR_FEED_TOKEN` if the provider requires a bearer token.
- **Settings → Secrets and variables → Actions → Variables**: `RADAR_DATA_RIGHTS_CONFIRMED` = `true`, but **only** after confirming the provider's license covers the intended use, derived calculations, data storage and display of sample links.
- If the feed **does not already label formats**, add `RADAR_ALLOW_METADATA_TAGGING = true` *only* if permitted by the provider; optionally provide `OPENAI_API_KEY` as a secret for AI-assisted title/description tagging. Without that setting, only provider-supplied `format_id` labels are used.

The collector calls your HTTPS feed with query parameters `start` and `end`, expressed as UTC ISO timestamps for the reporting month. A feed response should look like:

```json
{
  "source_name": "Your licensed trend-data provider",
  "videos": [
    {
      "id": "provider-video-id-123",
      "platform": "TikTok",
      "url": "https://www.example.com/a/real-video-url",
      "title": "My 30 day transformation",
      "description": "A brief description",
      "channel_id": "creator-123",
      "channel": "Creator name",
      "published_at": "2026-10-15T12:00:00Z",
      "duration": 45,
      "views": 150000,
      "likes": 12000,
      "comments": 240,
      "niches": ["Fitness", "Lifestyle"],
      "format_id": "transformation",
      "confidence": 0.95
    }
  ]
}
```

The URL is an **example schema, not a configured real service**. Any data vendor or your own authorized backend can implement it. `format_id` must match an ID from `scripts/taxonomy.json`. The sample numbers above are fictional documentation examples, not real statistics.

### Source selection

The script chooses a source in this order:

1. `--fixture FILE` (offline tests only; **never** publishes data).
2. `RADAR_FEED_URL` with confirmed rights (recommended for live use).
3. YouTube Data API, **only when** `YOUTUBE_DERIVED_METRICS_APPROVED=true`, `RADAR_DATA_RIGHTS_CONFIRMED=true` and `YOUTUBE_API_KEY` are present. This option is for developers who have independently obtained the relevant YouTube approvals, not ordinary API key owners.

Missing rights/credentials, fewer than 30 valid videos, or fewer than 3 evidenced formats are treated as a **failed refresh**, leaving the existing site and data intact. Override the quality thresholds with `--min-videos`, `--min-formats`, `--min-creators` for experiments.

## 4. Trigger a refresh and test

Run immediately with GitHub's **Actions → Monthly Format Radar + Pages → Run workflow** and `refresh_data = true`. After a successful run, the current site and its archived issues will update automatically.

For local automation tests:

```bash
python -m unittest discover -s tests -v
python scripts/refresh.py --dry-run
```

The second command will require an authorized data source configured in your environment. For the offline fixture example, see `tests/`.

### Ranking methodology

Only videos published within the completed calendar month are considered. Entries with fewer than **two distinct creators** are excluded (changeable configuration). Each format is scored on a 0–100 independent research scale:

| Component | Weight | How it is calculated |
|---|---:|---|
| Observed views per day | 38% | Median of `observed_views / days_since_publication`, log-transformed and capped at 1M/day |
| Engagement proxy | 22% | Average `(likes + 2 × comments) / views`, capped at 8% for scoring |
| Independent creator adoption | 25% | Log-scaled distinct creators, capped at 20 |
| Niche breadth | 15% | Distinct sampled niches, capped at 8 |

**Important limitations:** This is a ranking of formats *in the connected feed's sample*, not an objective global top-50. The platform(s) included depend on the feed. Views per day is a proxy using observed cumulative views, not measured monthly growth. View/like definitions differ across platforms. Inferring formats from titles can be wrong; check the provided examples before copying ideas. If fewer than 50 formats meet the evidence threshold, the site shows fewer than 50. The remaining starter examples are not padded into a live ranking.

### Archiving

- `site/data/latest.json`: active issue
- `site/data/index.json`: list of available real reports
- `site/data/archive/YYYY-MM.json`: archived issued report

The site automatically loads the most recent issue; the dropdown opens archived issues. **Historical data may only be retained if the feed's license expressly permits it.**

## Source policy and safety notes

YouTube's developer policies generally prohibit unapproved independent scores, data aggregation, and inferred content categories from YouTube API data. They also restrict storage of non-authorized data beyond 30 days. Those policies can include explicit additional permissions following an accepted developer audit. Therefore this repository **does not unlock YouTube-based derived rankings merely by supplying a YouTube API key**.

Relevant first-party references:

- [YouTube Data API search](https://developers.google.com/youtube/data/reference/rest/v3/search/list)
- [YouTube Developer Policies](https://developers.google.com/youtube/terms/developer-policies)
- [YouTube policy compliance guide](https://developers.google.com/youtube/terms/developer-policies-guide)
- [GitHub Pages custom workflow](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [GitHub Actions scheduled workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onschedule)

## Project map

```text
site/                     The website (HTML, CSS, JavaScript; no build needed)
  data/latest.json        Starter demo, replaced with first valid report
  data/index.json         Report manifest
  data/archive/           Automatically populated monthly reports
scripts/taxonomy.json     The 50 allowed content-format families
scripts/refresh.py        Collector, optional classifier, ranker, archival writer
scripts/seed.py           Regenerate starter demo and taxonomy (will reset latest!)
tests/test_refresh.py     Unit tests
.github/workflows/site.yml  Monthly automation and GitHub Pages deployment
```

The UI runs on a static page; the server-side collector is a GitHub Actions script. API credentials must never be pasted into HTML or committed to the repository.
