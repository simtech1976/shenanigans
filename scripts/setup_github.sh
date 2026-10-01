#!/usr/bin/env bash
# One-off setup of labels, milestones and starting issues for the GitHub
# Project. Requires the GitHub CLI, logged in: gh auth login
# Run from the repository folder: bash scripts/setup_github.sh
set -euo pipefail

echo "Creating labels..."
gh label create "bug" --color d73a4a --description "Something isn't working" --force
gh label create "enhancement" --color a2eeef --description "New feature or improvement" --force
gh label create "security" --color b60205 --description "Security-related" --force
gh label create "database" --color 5319e7 --description "Supabase SQL changes" --force
gh label create "rules" --color fbca04 --description "Game rules (rules.py)" --force
gh label create "ui" --color 0e8a16 --description "Pages and layout" --force
gh label create "docs" --color 0075ca --description "Documentation" --force
gh label create "chore" --color ededed --description "Maintenance and setup" --force

echo "Creating milestones..."
for m in "v0.10.0 Characters" "v0.11.0 Spells and inventory" "v0.12.0 Table polish" "v1.0.0 Campaign-ready"; do
  gh api "repos/{owner}/{repo}/milestones" -f title="$m" >/dev/null 2>&1 || echo " (milestone '$m' already exists)"
done

echo "Creating starting issues..."
issue() { gh issue create --title "$1" --label "$2" --milestone "$3" --body "$4" >/dev/null && echo " + $1"; }
issue "Character creation" "enhancement,ui" "v0.10.0 Characters" "Players (and the GM, for NPCs) create characters with name, species and notes."
issue "Character sheet with stats and roll buttons" "enhancement,ui,rules" "v0.10.0 Characters" "Main stats with skills grouped underneath, icons, D6/D20 roll buttons and the points balance. Uses character_service.load_sheet and rules.roll."
issue "Spend points from the character sheet" "enhancement,rules" "v0.10.0 Characters" "Upgrade buttons showing the cost, using rules.plan_upgrade and apply_stat_change."
issue "Direct editing on the sheet when allowed" "enhancement,rules" "v0.10.0 Characters" "When the GM enables player editing, players set values directly (rules.plan_direct_edit)."
issue "Choose abilities for a character" "enhancement,ui" "v0.10.0 Characters" "Pick from the game's abilities list."
issue "Spells: GM list and characters learning spells" "enhancement,ui" "v0.11.0 Spells and inventory" "Tables already exist (spells, character_spells)."
issue "Inventory on characters" "enhancement,ui" "v0.11.0 Spells and inventory" "Items with quantities (inventory_items table exists)."
issue "Post dice rolls to the activity feed" "enhancement" "v0.11.0 Spells and inventory" "Optional per game."
issue "GM title per game in the activity feed" "enhancement,database" "v0.12.0 Table polish" "e.g. 'The Narrator awarded 5 points to Han'."
issue "Option for the party to see each other's sheets" "enhancement,database" "v0.12.0 Table polish" "Per-game switch; one RLS policy change."
issue "Set up custom SMTP for emails" "chore,security" "v1.0.0 Campaign-ready" "Needed so all players receive confirmation and password reset emails, and to edit the reset template."
echo "Done. Now create the Project (see README: Project management) and add these issues to it."
