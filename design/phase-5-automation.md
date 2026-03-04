# Phase 5 — GitHub Actions Automation

## Goal

Automate the trading bot to run every 30 minutes during US market hours (Mon-Fri). The workflow fetches the code, installs dependencies, runs the bot, and commits the updated state + data files back to the repo.

## Depends On

- Phase 4: `bot/main.py` runs successfully locally

## What the Next Phase Expects

- `.github/workflows/trade.yml` exists and is functional
- The bot runs on schedule and commits state/data changes automatically
- GitHub secrets are configured: `TRADING212_API_KEY`, `TRADING212_API_SECRET`, `GEMINI_API_KEY`

## Files to Create

### 1. `.github/workflows/trade.yml`

```yaml
name: Trading Bot

on:
  schedule:
    # Every 30 minutes, Mon-Fri, during US market hours (UTC)
    # US market: 9:30 AM - 4:00 PM ET = ~14:30 - 21:00 UTC
    - cron: '*/30 14-21 * * 1-5'
  workflow_dispatch:  # Manual trigger for testing

permissions:
  contents: write  # Required to commit state.json and data/

jobs:
  trade:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run trading bot
        env:
          TRADING212_API_KEY: ${{ secrets.TRADING212_API_KEY }}
          TRADING212_API_SECRET: ${{ secrets.TRADING212_API_SECRET }}
          TRADING212_ENVIRONMENT: demo
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: python -m bot.main

      - name: Commit updated state and data
        run: |
          git config user.name "trading-bot"
          git config user.email "bot@noreply.github.com"
          git add state.json data/
          git diff --staged --quiet || git commit -m "bot: update state $(date -u +%Y-%m-%dT%H:%M:%SZ)"
          git push
```

## Configuration — GitHub Secrets

Go to your repository on GitHub, then:

1. Navigate to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret** for each:

| Secret Name | Value | Where to Get It |
|-------------|-------|-----------------|
| `TRADING212_API_KEY` | Your Trading212 API key ID | Trading212 app → Settings → API |
| `TRADING212_API_SECRET` | Your Trading212 API secret | Shown once when you create the key |
| `GEMINI_API_KEY` | Your Google Gemini API key | https://aistudio.google.com/apikey |

## Cron Schedule Reference

The cron `*/30 14-21 * * 1-5` means:

| Field | Value | Meaning |
|-------|-------|---------|
| Minute | `*/30` | Every 30 minutes (0, 30) |
| Hour | `14-21` | From 14:00 to 21:59 UTC |
| Day of month | `*` | Every day |
| Month | `*` | Every month |
| Day of week | `1-5` | Monday through Friday |

To adjust for different markets:
- **London (LSE)**: `*/30 8-16 * * 1-5`
- **US (NYSE/NASDAQ)**: `*/30 14-21 * * 1-5`
- **Both**: `*/30 8-21 * * 1-5` (wider window, more Actions minutes used)

## Budget Check

- ~15 runs/day × 20 trading days = **300 runs/month**
- ~2 minutes per run = **600 minutes/month**
- GitHub free tier: **2,000 minutes/month**
- Headroom: **1,400 minutes remaining** (70% of budget unused)

## Important Notes

- `workflow_dispatch` allows you to trigger the workflow manually from the GitHub Actions UI — use this for testing
- The commit step uses `git diff --staged --quiet ||` to skip the commit if nothing changed (prevents empty commits)
- `TRADING212_ENVIRONMENT: demo` is hardcoded in the workflow — change to `live` only after thorough testing on demo
- GitHub Actions cron can be delayed by a few minutes — this is expected and acceptable for 30-minute intervals

## Verification

1. Push all code to your GitHub repository
2. Add the three secrets in Settings → Secrets
3. Go to **Actions** tab
4. Click on "Trading Bot" workflow
5. Click **"Run workflow"** → **"Run workflow"** (manual trigger)
6. Watch the run logs — should show the bot analyzing each stock
7. After the run completes, check that `state.json` and `data/` files were updated in the repo (look for a commit from "trading-bot")

If the manual run succeeds, the scheduled cron will work the same way automatically.
