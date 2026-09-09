#!/usr/bin/env bash
# Rebuild and publish the GitHub Pages site.
#
# The site is a BUILD, assembled from two branches, so pushing to master or
# san-ramon does not update it on its own -- run this. That is the one cost of
# serving two cities from one repo, and it is why gh-pages carries a warning in
# its commit message rather than being editable by hand.
#
# Layout, and why:
#   /                 chooser page (lives in this script, below)
#   /app/             Los Angeles, from master, at the SAME paths Pages served
#                     when it was pointed at master -- so links already shared
#                     still resolve. Do not move this.
#   /sanramon/app/    San Ramon, from san-ramon
#   /contracosta/app/ Contra Costa County, from contra-costa
#   /bakersfield/app/ Bakersfield, from bakersfield
#
# Each app reads ../data/, so each city needs its data one level up from its
# app/. Only the three files an app actually fetches are copied; the pipeline's
# rasters, building footprints and CSVs are not part of the site.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD="$(mktemp -d)"
trap 'rm -rf "$BUILD"' EXIT
cd "$REPO"

command -v git >/dev/null || { echo "git not found"; exit 1; }

# --- guardrail: never publish from a stale copy of this script -------------
# Every city branch carries a copy of deploy.sh so it can be run from any
# checkout, but only the copy on contra-costa is canonical. An older copy that
# knows fewer cities would happily build a two-city site and force-push it
# over the four-city one (this happened on 2026-09-08). So: refuse unless this
# file is byte-identical to contra-costa:deploy.sh.
CANON="$(git show contra-costa:deploy.sh 2>/dev/null)" || { echo "cannot read contra-costa:deploy.sh"; exit 1; }
if [ "$CANON" != "$(cat "${BASH_SOURCE[0]}")" ]; then
  echo "REFUSING: this deploy.sh differs from contra-costa:deploy.sh (the canonical copy)."
  echo "Run it from a contra-costa checkout, or copy that file onto this branch first."
  exit 1
fi
# Every city branch this script builds from must exist locally AND be the
# version you think it is: warn loudly if a branch is behind its remote.
git fetch -q origin 2>/dev/null || echo "warning: could not fetch origin; building from local branches as-is"
for b in master san-ramon contra-costa bakersfield; do
  if git rev-parse --verify -q "origin/$b" >/dev/null && \
     [ "$(git rev-parse "$b")" != "$(git rev-parse "origin/$b")" ]; then
    echo "note: local $b ($(git rev-parse --short "$b")) != origin/$b ($(git rev-parse --short "origin/$b")); building from LOCAL"
  fi
done
git rev-parse --verify master   >/dev/null 2>&1 || { echo "no master branch";   exit 1; }
git rev-parse --verify san-ramon >/dev/null 2>&1 || { echo "no san-ramon branch"; exit 1; }
git rev-parse --verify contra-costa >/dev/null 2>&1 || { echo "no contra-costa branch"; exit 1; }
git rev-parse --verify bakersfield >/dev/null 2>&1 || { echo "no bakersfield branch"; exit 1; }

echo "building into $BUILD"
mkdir -p "$BUILD/data" "$BUILD/sanramon/data" "$BUILD/contracosta/data" "$BUILD/bakersfield/data"

# --- Los Angeles (master) ---
git archive master app/ | tar -x -C "$BUILD"
for f in la.geojson centers.geojson boundary.geojson; do
  git show "master:data/$f" > "$BUILD/data/$f"
done

# --- San Ramon (san-ramon) ---
git archive san-ramon app/ | tar -x -C "$BUILD/sanramon"
for f in sanramon.geojson centers_sanramon.geojson boundary_sanramon.geojson; do
  git show "san-ramon:data/$f" > "$BUILD/sanramon/data/$f"
done

# --- Contra Costa County (contra-costa) ---
git archive contra-costa app/ | tar -x -C "$BUILD/contracosta"
for f in contracosta.geojson centers_contracosta.geojson boundary_contracosta.geojson; do
  git show "contra-costa:data/$f" > "$BUILD/contracosta/data/$f"
done

# --- Bakersfield (bakersfield) ---
git archive bakersfield app/ | tar -x -C "$BUILD/bakersfield"
for f in bakersfield.geojson centers_bakersfield.geojson boundary_bakersfield.geojson; do
  git show "bakersfield:data/$f" > "$BUILD/bakersfield/data/$f"
done

# .nojekyll: Pages runs Jekyll by default and Jekyll drops underscore-prefixed
# paths. Nothing here starts with one today; that is not a reason to find out.
touch "$BUILD/.nojekyll"
cp "$REPO/site/index.html" "$BUILD/index.html"

for f in index.html app/index.html sanramon/app/index.html \
         contracosta/app/index.html bakersfield/app/index.html data/la.geojson \
         sanramon/data/sanramon.geojson contracosta/data/contracosta.geojson \
         bakersfield/data/bakersfield.geojson; do
  [ -s "$BUILD/$f" ] || { echo "MISSING or empty: $f"; exit 1; }
done

# Never publish a site with fewer city folders than the one currently live.
PREV="$(git ls-tree --name-only origin/gh-pages 2>/dev/null | grep -cE '^(app|sanramon|contracosta|bakersfield)$' || true)"
NOW="$(ls -d "$BUILD"/app "$BUILD"/sanramon "$BUILD"/contracosta "$BUILD"/bakersfield 2>/dev/null | wc -l | tr -d ' ')"
if [ -n "$PREV" ] && [ "$NOW" -lt "$PREV" ]; then
  echo "REFUSING: new build has $NOW city folders, live site has $PREV."; exit 1
fi

cd "$BUILD"
git init -q -b gh-pages
git remote add origin "$(git -C "$REPO" remote get-url origin)"
git add -A
git commit -q -m "Build: LA /app/, San Ramon /sanramon/, Contra Costa /contracosta/, Bakersfield /bakersfield/

Generated by deploy.sh from master ($(git -C "$REPO" rev-parse --short master)),
san-ramon ($(git -C "$REPO" rev-parse --short san-ramon)), contra-costa
($(git -C "$REPO" rev-parse --short contra-costa)) and bakersfield
($(git -C "$REPO" rev-parse --short bakersfield)). Do not edit this branch
by hand -- the next deploy force-pushes over it."
git push -q --force origin gh-pages

echo
echo "pushed. Pages usually takes 1-2 minutes."
echo "  https://advikar.github.io/coolequity/"
echo "  https://advikar.github.io/coolequity/app/             (Los Angeles)"
echo "  https://advikar.github.io/coolequity/sanramon/app/    (San Ramon)"
echo "  https://advikar.github.io/coolequity/contracosta/app/ (Contra Costa County)"
echo "  https://advikar.github.io/coolequity/bakersfield/app/ (Bakersfield)"
