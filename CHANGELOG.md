# Changelog

All notable changes to RPG Tables are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project uses [Semantic Versioning](https://semver.org/). While the
version is below 1.0.0, new features increase the minor number (0.9.0 →
0.10.0) and fixes increase the patch number (0.10.0 → 0.10.1).

Versions 0.1.0 to 0.8.0 are development milestones reconstructed from the
project's history; 0.9.0 is the first tagged release.

## [Unreleased]

### Added
- Version number shown in the app's sidebar, with a "What's new" page that
  displays this changelog.
- Project management: issue templates for bugs and feature requests, and a
  roadmap (`ROADMAP.md`).

## [0.9.0] - 2026-10-01

### Added
- **Players tab** on the game page: the GM sees everyone with an account, with
  a filter box, and invites them with one click; sees each member's status and
  which character they play; can cancel invitations and remove players.
  Players can leave a game.
- **Decline** button for invitations on the My games page.
- **My profile** page: change username, set an avatar emoji and a short
  "about me", see sign-in methods, and change password (email accounts).
- **Welcome step**: people signing in with Microsoft or Discord for the first
  time choose their username before continuing.
- **Sign in with Microsoft and Discord** using the secure PKCE flow, designed
  for Streamlit's session model (single-use, server-side tickets).
- **Forgotten password** reset using a code sent by email (works reliably
  with Streamlit and isn't consumed by email security scanners).
- Usernames for social sign-ins are generated from display names (never email
  addresses), with a suffix added automatically if a name is taken.

### Changed
- Usernames are unique regardless of capital letters ("Han" and "han" can't
  both exist) and can't start or end with spaces. Existing clashes are renamed
  with a suffix and their owners asked to choose a new name.
- Sign-up and profile pages share the same username rules: 3–30 characters of
  letters, numbers, spaces, hyphens, underscores and full stops.
- Minimum password length is 8 characters.

### Removed
- Apple and Google sign-in (Apple requires a paid developer membership; Google
  requires a credit card on the Cloud account). Google can be re-enabled
  through settings alone.

### Security
- Usernames are displayed literally, so formatting characters in a name can't
  change how the page renders.

## [0.8.0] - 2026-10-01

### Added
- **Icons** for main stats, skills and abilities: an emoji, an uploaded image
  (PNG, JPG or WebP, up to 1 MB), or both. Default stats come with emoji.
- **Edit** option for abilities (previously add and delete only).
- **`supabase_reset.sql`**: deletes all game data and rebuilds the database in
  a single all-or-nothing transaction, keeping user accounts.

### Changed
- Uploaded icons are stored in the game's own private folder; the database
  refuses icons pointing at another game's files.
- All icons on a page are signed in a single request.

## [0.7.0] - 2026-09-30

### Added
- **`rules.py`**: all game rules in pure Python (levels, pips, skill bonuses,
  upgrade costs, rolls, building the character sheet, planning changes), with
  16 unit tests (`pytest`).
- **`character_service.py`**: loads character sheets and saves planned changes.
- **`apply_stat_change`** database function: saves a stat change, its cost and
  its activity entry together; refuses negative costs and balances; only lets
  spending raise a stat.
- **`supabase_setup.sql`**: a single script that builds the entire database.
- `roll_d20` for D20 games (1d20 + modifier).

### Changed
- **Game rules moved from the database to the app.** The database now enforces
  integrity only (permissions, valid values, atomic spending, logging).
- The "flat numbers" dice system is now **D20**.
- Changes made outside the app (for example in the Supabase dashboard) are
  still logged by a safety-net trigger.

### Removed
- `upgrade_stat`, the SQL cost function and the `character_sheet_stats` view
  (replaced by `rules.py` and `apply_stat_change`).
- `dice.py` (replaced by `rules.py`).

## [0.6.0] - 2026-09-27

### Added
- **Stats & skills tab**: the GM adds game-specific main stats and skills
  (including skills under default main stats), and edits, moves, reorders and
  deletes them. Players see the same list read-only.
- **Dexterity** as a default main stat, with Dodge, Stealth and Sleight of
  Hand; Jumping and Swimming as default Strength skills.
- Activity entries when the GM adds, renames, moves or removes stats.

### Changed
- **Skills are stored as a bonus above their main stat**, so raising a main
  stat raises all its skills by the same amount, and an unimproved skill
  always equals its main stat.

### Fixed
- Deleting a skill that characters had values for failed, because the
  activity log looked up the skill after it had been removed.

## [0.5.0] - 2026-09-27

### Added
- **Skill points**: starting points per character (set by the GM when
  creating a game), end-of-session awards by the GM, and an append-only
  points ledger with full history.
- **Upgrade costs set per game**: points per die for skills and for main
  stats; three pips roll over into a die.
- **Player sheet editing** switch per game: when on, players can edit their
  own stats directly.
- **Activity log** visible to every member, with pop-up notifications every
  30 seconds; messages use character names; direct edits are highlighted.

### Security
- Players can't award themselves points or change stats outside the rules;
  every change is recorded automatically by the database.

## [0.4.0] - 2026-09-27

### Added
- **My games** page: list of your games with cover images and roles,
  pending invitations with Accept, and a form to create a game.
- **Game page** with the GM's edit form, cover image, description (Markdown),
  notes with a visible-to-players switch, and abilities.
- **Private image storage** for game covers, served through short-lived
  signed URLs; only members can view a game's images.
- Selectable **abilities** (traits like Force Sensitive) per game.

## [0.3.0] - 2026-09-26

### Added
- **D6 dice system**: dice codes like 4D+2, roll buttons, and a choice of
  dice system per game.

## [0.2.0] - 2026-09-24

### Added
- **Core database**: profiles, games, members (roles per game, so someone can
  be GM of one game and a player in another), stat definitions (main stats and
  skills; defaults shared by every game, plus game-specific ones), characters,
  character stats, spells and inventory.
- **Row Level Security** on every table: everything requires login; members
  see only their own games; character sheets are private to their owner and
  the GM; the GM creates the game and becomes its GM automatically.
- Default stats: Strength, Intelligence, Mechanical and Technical, with skills.

## [0.1.0]- 2026-09-22

### Added
- Streamlit app connected to Supabase, with keys kept in Streamlit secrets.
- Email sign-up (with confirmation) and log in.
- Navigation that only shows app pages to logged-in users.

### Fixed
- Form fields sometimes lost their values; login and sign-up now use forms.

### Security
- The Supabase client is created per user session; a shared cached client
  could have mixed up different users' logins.

[Unreleased]: https://github.com/simtech1976/shenanigans/compare/v0.9.0...HEAD
[0.9.0]: https://github.com/simtech1976/shenanigans/releases/tag/v0.9.0
