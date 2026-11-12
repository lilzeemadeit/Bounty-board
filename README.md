# Bounty Board

A One Piece Card Game deck builder: search every card (by name, number, type or what it does), build decks by leader with several builds each, track your collection, make Buy Lists, and save cards to your ☆Treasure Box☆. Sign in to sync across devices.

**Open the app:** https://lilzeemadeit.github.io/Bounty-board/ (on a phone, use “Add to Home Screen”).

## How it's put together
- `src/app-template.html`: the whole app (one page, no build tools).
- `tools/build_data.py`: turns the official English card list (community scrape at [buhbbl/punk-records](https://github.com/buhbbl/punk-records)) into `tools/cards.json`.
- `tools/build_pages.py`: combines the two into `index.html`.
- `.github/workflows/refresh-cards.yml`: refreshes the card data every night.
- `events.json`: the countdowns on the Home page. Edit it on GitHub (open the file, click the pencil, then **Commit changes**) to add your own. Each event is one line inside the brackets, with a comma between lines:
  `{"name": "Locals tournament", "date": "2026-11-15", "note": "Game store"}`
  The date is year-month-day; `note` is optional. Events disappear the day after they happen.
- `wallpapers/`: pictures you put here become built-in background choices in the app (see the README in that folder). The `Update wallpapers` action makes phone-sized copies in `wp/`.
- Accounts and saved data: Supabase (email + password, each person can only read their own data).

Card names, text and images are © Eiichiro Oda/Shueisha, Toei Animation and Bandai. This is an unofficial fan tool.
