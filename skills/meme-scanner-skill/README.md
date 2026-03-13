# Meme Scanner Skill

Discover and analyze meme tokens on Solana.

## Quick Start

```bash
# Scan new listings
python scripts/scan_new_listings.py --dex raydium --hours 24

# Score a token
python scripts/score_meme.py --mint <TOKEN_MINT>

# Track social mentions
python scripts/track_twitter.py --token $MEME --hours 24
```

## Documentation

See [SKILL.md](./SKILL.md) for full workflow documentation.

## Scripts

| Script | Description |
|--------|-------------|
| `scan_new_listings.py` | DEX new listing scanner |
| `launch_monitor.py` | Real-time launch watch |
| `track_twitter.py` | Twitter mention tracker |
| `analyze_telegram.py` | Telegram sentiment |
| `social_score.py` | Combined social metrics |
| `analyze_holders.py` | Holder distribution |
| `track_creator.py` | Creator wallet tracking |
| `detect_bundles.py` | Bundle/bot detection |
| `score_meme.py` | Full meme token score |
| `rank_launches.py` | Launch ranking |
| `daily_report.py` | Daily opportunity report |

## License

MIT
