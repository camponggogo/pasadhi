# Publishing PASADHI on GitHub

The local repository is already initialised and committed. Two things are left, and both need the account that
owns the new repository — this sandbox has no push credential for `camponggogo`, so the commands below are for you
(or paste a fine-grained PAT into `deploy/.github_token` and ask me to run them).

## 1. Create the repository

**Option A — web UI (30 s).** <https://github.com/new> → owner `camponggogo` → name **`pasadhi`** →
description *“Virtual distributed machine for old hardware: matrix-first, process-layered.”* → Public →
**do not** initialise with a README (the local repo already has one) → Create.

**Option B — GitHub CLI.**

```bash
gh repo create camponggogo/pasadhi --public \
  --description "Virtual distributed machine for old hardware: matrix-first, process-layered."
```

## 2. Push

```bash
cd D:/Projects/Petals_Distributed_Inference/pasadhi
git remote add origin https://github.com/camponggogo/pasadhi.git
git push -u origin main
```

## 3. Mark the SUAY provenance

PASADHI is a fork-in-spirit, not a GitHub "fork" (a real fork would drag SUAY's whole history and its AI-only
framing along). Record the relationship instead:

- `README.md` already links SUAY and the MIT licence.
- Add a `NOTICE` file: *“PASADHI is derived from SUAY (github.com/camponggogo/suay), MIT. The control plane,
  measurement harness and licence text originate there.”*
- In the SUAY repository, add to its README: *“Successor project: PASADHI — github.com/camponggogo/pasadhi.”*
- Optional: GitHub → SUAY → Settings → General → **Template repository**, and mark PASADHI's README as
  “built on SUAY” in the About box.

## 4. Rename the project in the old tree (optional)

If you also want the SUAY website and dashboard to say **ปัสสัทธิ / PASADHI**, say which surfaces:
the landing page (11 languages), the dashboard title, the API key prefix (`suay_` → `psd_`), or all of them.
Renaming API key prefixes is a breaking change for existing keys and needs a migration step.
