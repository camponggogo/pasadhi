# Pushing PASADHI to GitHub

The local repository has 13 commits and is ready. The remote is already configured:

```
origin  https://github.com/camponggogo/pasadhi.git
```

The repository does **not exist yet** (`GET /repos/camponggogo/pasadhi` → 404), and this machine has no
credential for the `camponggogo` account: the stored tokens belong to `campong-hot` and
`livestocknextplus-creator` (both 403), and password auth to the web host is the hosting account, not GitHub.

## Option A — create the repository, then push (2 minutes)

1. Open <https://github.com/new> (signed in as camponggogo).
2. Name **pasadhi**, Public, **do not** add a README or a licence (the local repo has both).
3. Create, then from this folder:

```bash
cd D:/Projects/Petals_Distributed_Inference/pasadhi
git push -u origin main
```

If the command asks for credentials, sign in through GitHub Desktop instead: open this folder in the app and
press **Ctrl+P** (it holds a working session for camponggogo).

## Option B — let the agent push

Save a fine-grained personal access token for `camponggogo` (Contents: read and write, repository `pasadhi`)
to `deploy/.github_token`. The file is already ignored by git. Then:

```bash
python scripts/push_with_stored_credential.py --target deploy/.github_token
```

## After the first push: cut the release

```bash
git tag v0.1.0
git push origin v0.1.0
```

The workflow at `.github/workflows/release.yml` then builds and attaches:

- `PASADHI-windows-x64.zip` (PyInstaller one-file)
- `PASADHI-linux-x64.tar.gz`
- `PASADHI-macos.tar.gz`
- `PASADHI-android` (Briefcase APK, best effort)

Until that runs, the site serves the portable Windows build and the source zip from
`/projects/pasadhi/download/` so the download buttons work.
