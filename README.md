# RPG Tables

A Streamlit + Supabase app for running tabletop role-playing games: game masters
create games, invite players, define stats and skills (including D6 dice codes),
award points, and everyone sees a transparent activity log of character changes.

## Project layout

```
app.py               Entry point: login gate and page navigation
db.py                Supabase client (one per user session) and image storage helpers
rules.py             ALL game rules: pips, skills, costs, rolling (pure Python)
character_service.py Loads character sheets; saves changes planned by rules.py
stat_manager.py      Loads stats/skills and renders the "Stats & skills" tab
icons.py             Emoji / uploaded icons for stats, skills and abilities
players_tab.py       Players tab: invite, remove and leave
oauth.py             Sign in with Google, Microsoft and Discord
tests/               Unit tests for rules.py (run: pytest)
views/login.py       Log in / sign up
views/my_games.py    Your games, invitations, create a game
views/profile.py     My profile: username, avatar, bio, password; welcome step
views/game.py        Game page: notes, players, stats & skills, abilities, activity, awards
version.py           The app's version number (shown in the sidebar)
CHANGELOG.md         What changed in each version (also shown in the app)
ROADMAP.md           What's planned for upcoming versions
.github/             Issue templates for bug reports and feature requests
scripts/             One-off GitHub setup (labels, milestones, issues)
supabase_setup.sql   Complete database setup (run once on a new project)
supabase_reset.sql   ⚠️ Deletes all game data and rebuilds the database
```

## Setup

1. **Create a Supabase project** at supabase.com.

2. **Build the database.** In the dashboard open *SQL Editor*, paste the whole of
   `supabase_setup.sql` and click *Run*. Edit the default stats at the bottom of
   the file first if you want a different set.

3. **Configure authentication.** Under *Authentication → Sign In / Providers*
   make sure Email is enabled. Under *Authentication → URL Configuration* set the
   *Site URL* (and add it to *Redirect URLs*) to where the app runs:
   - locally: `http://localhost:8501`
   - Codespaces: the forwarded URL from the *Ports* tab, e.g.
     `https://<codespace-name>-8501.app.github.dev`
   - once deployed: your app's URL

   Under *Authentication → Emails → Templates → Reset Password*, replace the
   message body with a template that shows the code `{{ .Token }}` (see
   "Password reset" below), because the app resets passwords with a code rather
   than a link.

   The built-in email sender is rate-limited; set up custom SMTP before real
   users sign up. For testing you can add users under *Authentication → Users →
   Add user* with "Auto confirm user" ticked.

4. **Add your keys.** Copy `.streamlit/secrets.toml.example` to
   `.streamlit/secrets.toml` and fill in your Project URL and publishable (anon)
   key from *Project Settings → API*.

5. **Install and run:**
   ```bash
   pip install -r requirements.txt
   streamlit run app.py
   ```
   Always start it with `streamlit run`, not `python app.py`.

## Resetting the database

`supabase_reset.sql` **permanently deletes all game data** (games, characters,
notes, points, activity and uploaded images) and rebuilds everything from
scratch, which is useful after testing or to start a new season. Paste it into
the SQL Editor and run it.

- User accounts are kept. Email users keep their usernames; Microsoft and
  Discord users are asked to choose theirs again at their next sign-in. To delete accounts as well,
  uncomment the `delete from auth.users;` line in step R3.
- It runs as a single transaction: if anything fails, nothing is changed.
- If it stops and asks you to empty the image bucket, go to *Storage →
  game-images*, select all files, delete them, and run the script again.
  (Supabase can block deleting stored files from SQL.)

## Sign in with Google, Microsoft and Discord

Each provider needs an app registered in its developer console, with this
**callback URL** (find your project ref in *Project Settings*):

```
https://<project-ref>.supabase.co/auth/v1/callback
```

Then in Supabase open *Authentication → Sign In / Providers*, enable the
provider and paste in its client ID and secret.

**Google** (free): Google Cloud Console → *APIs & Services* (Google Auth
Platform) → set up the consent screen/branding → *Clients* / *Credentials* →
create an OAuth client of type **Web application** → add the callback URL as an
authorised redirect URI → copy the client ID and secret into Supabase.

**Microsoft** (free; "Azure" in Supabase): Azure portal / Microsoft Entra admin
center → *App registrations* → *New registration* → supported accounts:
**any organisational directory and personal Microsoft accounts** (so players
can use Outlook/Xbox accounts) → redirect URI type **Web** = the callback URL →
*Certificates & secrets* → new client secret (copy its **Value**, not its ID).
In Supabase paste the *Application (client) ID* and the secret; leave the tenant
URL empty. Client secrets expire (the portal lets you choose up to 2 years), so
note the date.

**Discord** (free): Discord Developer Portal → *New Application* → *OAuth2* →
copy the client ID, reset/copy the client secret, and add the callback URL
under *Redirects*.

**Then, in Supabase:** *Authentication → URL Configuration* → add each address
the app runs at to **Redirect URLs** with `/**` on the end, for example
`http://localhost:8501/**`, `https://<codespace-name>-8501.app.github.dev/**`
and your deployed URL. (Without this, providers return people to the Site URL
and sign-in fails with "link has expired".)

**Finally, in `.streamlit/secrets.toml`:** set `APP_URL` to where this copy of
the app runs, and list the providers to show, e.g.
`OAUTH_PROVIDERS = ["google", "azure", "discord"]`. Buttons only appear
for providers listed there.

Notes:
- The first time someone signs in with Microsoft or Discord, they're asked to
  choose a username before continuing (a temporary one is made from their
  display name, never their email). Anyone can change their username, avatar
  emoji and bio later under *My profile*.
- If someone signs in with a provider using the same email as an existing
  account, Supabase links them to the same account.
- The sign-in opens in a new tab; people can close the old one.

## Password reset

Players reset forgotten passwords from the *Forgot password* tab: they enter
their email, receive a numeric code, and enter it with a new password. Codes
work better than links with Streamlit (no redirect needed) and can't be used up
by email security scanners. Paste this into the *Reset Password* email template:

```html
<h2>Reset your password</h2>
<p>Enter this code in the app to choose a new password:</p>
<p style="font-size:28px;font-weight:bold;letter-spacing:6px">{{ .Token }}</p>
<p>The code expires shortly. If you didn't ask to reset your password, you can
ignore this email.</p>
```

## Deploying to Streamlit Community Cloud

Push the project to GitHub (secrets.toml is git-ignored), create the app on
share.streamlit.io, and paste the two lines from your `secrets.toml` into the
app's *Settings → Secrets*. Then update the Supabase Site URL to the app's URL.

## Security model

All permissions are enforced by Row Level Security in the database, not by the
app, so they hold even if someone bypasses the app entirely:

- The publishable key alone can read nothing; everything requires login.
- Only members see a game; hidden notes never leave the database for players.
- Character sheets are visible to their owner and the game master.
- Players change stats by spending points, or directly only if the game master
  enables player editing. Every change is logged in the game's activity feed,
  visible to all members, including edits made outside the app.
- `apply_stat_change` saves a stat change, its cost and its log entry together,
  refuses negative costs and balances, and only lets spending raise a stat.
- Points can only be awarded by the game master; the ledger is append-only.
- Game images live in a private bucket and are served via short-lived signed URLs.

## Where the logic lives

**Game rules live in `rules.py`**: what 4D+2 means, three pips rolling into a
die, skills as bonuses on their main stat, upgrade costs, and dice rolls. It is
pure Python with unit tests, so rules can be changed and tested without
touching the database:

```bash
pip install pytest
pytest
```

**The database enforces integrity only**: relationships, valid values, who may
do what, atomic point spending, and the activity log. It doesn't know D6 from
D20. If another front end (mobile app, Discord bot) is ever added, rules that
must be enforced for every client can be moved into the database then.

## Versions and releases

The project uses [Semantic Versioning](https://semver.org/). Until 1.0.0, new
features raise the middle number (0.9.0 → 0.10.0) and fixes raise the last
(0.10.0 → 0.10.1). Changes are recorded in `CHANGELOG.md` using the
[Keep a Changelog](https://keepachangelog.com/) format.

**While working:** add a line under `## [Unreleased]` in `CHANGELOG.md` for
each change, under *Added*, *Changed*, *Fixed*, *Removed* or *Security*.

**To release a version:**

1. In `CHANGELOG.md`, rename `## [Unreleased]` to `## [0.10.0] - YYYY-MM-DD`
   and add a fresh, empty `## [Unreleased]` above it. Update the links at the
   bottom (replace `OWNER/REPO` with your repository the first time).
2. Set the same number in `version.py`.
3. If the release includes database changes, note which `.sql` file to run.
4. Commit, tag and push:
   ```bash
   git add -A
   git commit -m "Release v0.10.0"
   git tag -a v0.10.0 -m "v0.10.0"
   git push origin main --tags
   ```
5. On GitHub: *Releases → Draft a new release*, choose the tag, and paste that
   version's section from `CHANGELOG.md` as the notes.

For the first release, tag the current state as `v0.9.0` in the same way.

## Project management

Work is tracked in one GitHub Project created from the **Iterative
development** template: features and bugs are issues in the same project,
told apart by labels, with a milestone for each planned version.

**One-off setup:**

1. Install the GitHub CLI and log in (`gh auth login`), then run
   `bash scripts/setup_github.sh` from the repository folder. It creates
   labels, milestones matching `ROADMAP.md`, and the starting issues.
2. On GitHub, open your profile or organisation → *Projects* → *New project*
   → **Iterative development**. Name it (e.g. "RPG Tables").
3. In the project's *⋯ → Settings → Manage access*, or from the repository's
   *Projects* tab, **link the repository**.
4. In the project's *⋯ → Workflows*, turn on **Auto-add to project** for the
   repository, so new issues appear automatically. Add the existing issues
   with *+ Add item → Add item from repository*.
5. Add two extra views (*+ New view*):
   - **Bugs**: table layout, filter `label:bug`, sorted by status.
   - **Roadmap**: roadmap layout, grouped by *Milestone*.

**Day to day:** report bugs and ideas with *Issues → New issue* (the templates
ask for the right details). Pick issues for the current iteration on the
board, move them across as you work, and mention the issue in the commit
(`Fixes #12`) so it closes automatically. When a milestone's issues are done,
release that version.
