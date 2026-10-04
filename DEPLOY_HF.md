# Deploying to Hugging Face Spaces (Docker — Flask / Design.md app)

This repo is ready to deploy as a **Docker Space**. The `Dockerfile`, the HF
metadata in `README.md`, `.gitattributes` (Git LFS), and the `$PORT`-aware
`server.py` are all in place.

## What's already configured
- **`Dockerfile`** — Python 3.11, CPU-only PyTorch, installs deps + the spaCy
  model, and **pre-bakes** the MiniLM and t5-small weights into the image so the
  first request is fast. Runs as uid 1000 and listens on port **7860**.
- **`README.md` frontmatter** — `sdk: docker`, `app_port: 7860`.
- **`.gitattributes`** — tracks `*.csv`, `*.jsonl`, `*.xlsx` via **Git LFS**
  (the 37 MB Flipkart CSV exceeds HF's 10 MB non-LFS limit).
- **`server.py`** — binds `0.0.0.0` on `$PORT` (default 7860).

## Steps

### 1. Create the Space
Go to https://huggingface.co/new-space →
- **Owner / Space name:** your choice (e.g. `material-harmonization`)
- **SDK:** **Docker** → **Blank**
- **Hardware:** CPU basic (free) is enough. If it feels tight under load, bump to
  a larger CPU.
- Create the Space. You'll get a git URL like
  `https://huggingface.co/spaces/<user>/material-harmonization`.

### 2. Push this folder to the Space
From the Dewro folder:

```bash
# one-time: install the HF CLI and git-lfs if needed
pip install -U huggingface_hub
git lfs install

# init and connect
git init
git lfs track "*.csv" "*.jsonl" "*.xlsx"   # already in .gitattributes
git add .
git commit -m "Material harmonization — Flask/Docker Space"

git remote add space https://huggingface.co/spaces/<user>/material-harmonization
git push space main
```

You'll be asked for a Hugging Face **access token** (create one at
https://huggingface.co/settings/tokens with *write* scope) as the git password.

### 3. Watch it build
The Space page shows build logs. First build takes several minutes (installing
torch/transformers + baking model weights). When it finishes, the app appears in
the Space's embedded view — the full Design.md UI, all five tabs working.

## Notes & gotchas
- **Image size:** ~2–3 GB because of torch + baked model weights. That's normal
  for an ML Space and well within HF's limits.
- **Free CPU tier** loads MiniLM + t5-small + spaCy into ~1–2 GB RAM. If you ever
  see out-of-memory on heavy pipeline runs, upgrade the Space hardware a notch.
- **Models baked at build time** → no network needed at request time, no cold
  download. If you'd rather slim the image and download on first use instead,
  remove the two `python -c "...download..."` lines from the `Dockerfile`.
- **`app.py` (Streamlit)** is still in the repo but unused by this Space; harmless.
  To deploy the Streamlit version instead, you'd use an `sdk: streamlit` Space
  pointing at `app.py` — ask and I'll set that up separately.
- **Secrets:** none required. The app uses only public model weights and the
  bundled datasets.
