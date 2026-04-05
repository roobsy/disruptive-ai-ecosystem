# Autonomous Disruptive Intelligence Ecosystem

A self-evolving, multi-agent AI system for unbounded scientific discovery and disruptive innovation.

## Phase 0: Foundation Setup

### Prerequisites

1. **Python 3.11+** — [Download Python](https://www.python.org/downloads/)
2. **Cursor IDE** — [Download Cursor](https://cursor.sh/) (optional but recommended; VS Code also works)
3. **Anthropic API Key** — [Get your key](https://console.anthropic.com/settings/keys)
4. **Supabase Account** — [Create free account](https://supabase.com/dashboard)

---

### Step-by-Step Setup

#### 1. Clone or download this project

Place it wherever you keep your projects:
```bash
cd ~/projects
# If you have git:
git init ecosystem
cd ecosystem
# Then copy all these files into it
# Or just open the folder in Cursor
```

#### 2. Create a Python virtual environment

```bash
# Create the virtual environment
python3 -m venv .venv

# Activate it
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### 3. Create your Supabase project

1. Go to [supabase.com/dashboard](https://supabase.com/dashboard)
2. Click **"New Project"**
3. Name it `ecosystem` (or whatever you prefer)
4. Set a database password (save it somewhere safe)
5. Choose the region closest to you
6. Wait for the project to be created (~2 minutes)

#### 4. Run the database schema

1. In your Supabase dashboard, click **"SQL Editor"** in the left sidebar
2. Click **"New Query"**
3. Copy the entire contents of `scripts/setup_supabase.sql` and paste it in
4. Click **"Run"** (or press Ctrl+Enter)
5. You should see "Success. No rows returned" — that means it worked

#### 5. Configure environment variables

```bash
# Copy the example file
cp .env.example .env

# Open it in your editor and fill in:
```

Edit `.env` with your values:

```
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-key-here
```

**Where to find your Supabase credentials:**
1. In your Supabase dashboard, go to **Settings** > **API**
2. Copy the **Project URL** → paste as `SUPABASE_URL`
3. Copy the **anon public** key → paste as `SUPABASE_KEY`

#### 6. Test the connection

```bash
# Quick test — this should print your venture info
python3 -c "
from core.kb import get_venture_id
vid = get_venture_id()
print(f'Connected! Venture ID: {vid}')
"
```

If you see a venture ID, everything is connected.

---

### Running Your First Extraction

Extract a paper from the vision correction display literature:

```bash
# The December 2024 paper on real-time computational VCD
python3 -m scripts.extract_paper 2501.01450

# The seminal MIT/Berkeley 2014 light field display paper
python3 -m scripts.extract_paper 1407.5765

# Add context to guide extraction focus
python3 -m scripts.extract_paper 2501.01450 --context "Focus on PSF deconvolution algorithms and their limitations for vision correction"
```

The script will:
1. Download the PDF from ArXiv
2. Send it to Claude with the Epistemic Filter prompt
3. Extract 10-30 knowledge claims, each labeled as Axiomatic Fact, Experimental Result, or Cognitive Framework
4. Store everything in your Supabase KB (knowledge base) with full provenance
5. Display a summary table showing what was extracted

### Checking Your KB

After extracting a few papers, check what's in your KB:

```bash
python3 -c "
from core.kb import get_venture_id, get_stats, get_nodes
vid = get_venture_id()

# Show overall stats
stats = get_stats(vid)
print(f'Total nodes: {stats[\"total\"]}')
print(f'By label: {stats[\"by_label\"]}')
print(f'By domain: {stats[\"by_domain\"]}')

# Show high-confidence axiomatic facts
facts = get_nodes(vid, epistemic_label='axiomatic_fact', min_confidence=80)
for f in facts:
    print(f'  [{f[\"confidence\"]}] {f[\"summary\"]}')
"
```

You can also view your data directly in the Supabase dashboard:
1. Go to **Table Editor** in the left sidebar
2. Click on `knowledge_nodes` to see all extracted knowledge
3. Click on `provenance` to see source tracking

---

### Suggested Papers for Initial KB

Here are key papers to extract for the vision correction venture:

```bash
# Core VCD research
python3 -m scripts.extract_paper 2501.01450   # Real-time computational VCD (Dec 2024)
python3 -m scripts.extract_paper 1407.5765    # MIT/Berkeley eyeglasses-free display (2014)

# Related computational imaging
python3 -m scripts.extract_paper 2404.12345   # Search for relevant papers at arxiv.org
```

Also search [Semantic Scholar](https://www.semanticscholar.org/) for:
- "vision correcting display"
- "computational aberration correction"
- "light field display vision"
- "PSF deconvolution display"

---

### Project Structure

```
ecosystem/
├── core/                   # Shared infrastructure
│   ├── model_router.py     # Standardized Agent Interface
│   ├── epistemic_filter.py # Labeling and confidence scoring
│   └── kb.py               # Supabase CRUD operations (KB)
├── extraction/             # Data acquisition
│   └── sources/
│       └── arxiv.py        # ArXiv paper downloader
├── scripts/
│   ├── setup_supabase.sql  # Database schema
│   └── extract_paper.py    # Main extraction script
├── config/
├── data/                   # Downloaded papers (git-ignored)
├── .env                    # Your secrets (git-ignored)
├── .env.example            # Template
├── .gitignore
├── requirements.txt
└── README.md
```

---

### What's Next (Phase 1)

Once you've extracted 5-10 papers and have a populated KB:

1. **Semantic search** — Add embeddings to enable "ask a question, find relevant knowledge"
2. **Optics Domain Agent** — A specialized agent with its own system prompt and domain expertise
3. **Master Brain** — The orchestrator that queries across domains and identifies gaps
4. **Challenge Loop** — Master Brain poses questions, Domain Agent responds with evidence

---

### Troubleshooting

**"SUPABASE_URL and SUPABASE_KEY must be set"**
→ Make sure your `.env` file exists and has the correct values. Run `cat .env` to verify.

**"Venture not found"**
→ Make sure you ran the `setup_supabase.sql` in the Supabase SQL Editor.

**"Could not parse JSON response"**
→ The Claude response wasn't valid JSON. Try running again — occasionally the model produces slightly malformed output. If persistent, check the raw response printed in the console.

**PDF download fails**
→ Some ArXiv papers have unusual IDs. Try using the full URL instead: `python3 -m scripts.extract_paper https://arxiv.org/abs/2501.01450`

**Cost concerns**
→ Each paper extraction costs approximately $0.02-0.08 depending on paper length. You can monitor your usage at [console.anthropic.com](https://console.anthropic.com/).
