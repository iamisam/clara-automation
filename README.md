# Clara Automation Pipeline

**Automated AI Voice Agent Configuration System for Service Trade Businesses**

This project automates the onboarding process for Clara Answers, an AI-powered voice agent. It processes demo and onboarding call recordings/transcripts to generate versioned agent configurations with zero manual intervention.

---

## 🎯 Project Overview

### What It Does

1. **Pipeline A (Demo → v1):** Processes demo call recordings/transcripts and generates preliminary agent configurations
2. **Pipeline B (Onboarding → v2):** Updates agent configurations based on onboarding calls with intelligent diff tracking
3. **Batch Processing:** Auto-discovers and processes multiple calls in a single execution
4. **Diff Viewer:** Interactive Streamlit dashboard showing side-by-side v1 vs v2 comparisons

### Key Features

- ✅ **Zero-cost**: Uses only free-tier tools (Ollama, Whisper, n8n, Streamlit Cloud)
- ✅ **Universal Input Handling**: Supports `.txt`, `.m4a`, `.mp4`, `.mp3`, `.wav` files
- ✅ **Automatic Transcription**: Uses Whisper for audio/video files
- ✅ **Smart Versioning**: v1 (demo) → v2 (onboarding) with changelog tracking
- ✅ **Idempotent**: Safe to run multiple times
- ✅ **Production-Ready**: File discovery, error handling, validation

---


## 📋 Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Orchestration** | n8n (Docker) | Workflow automation |
| **Transcription** | Faster Whisper (small model) | Audio/video → text |
| **LLM** | Ollama + Llama 3 | Data extraction |
| **API Wrapper** | Flask | Python script execution endpoint |
| **UI Dashboard** | Streamlit | Interactive diff viewer |
| **Storage** | Filesystem | Versioned JSON outputs |
| **Container** | Docker + Docker Compose | n8n + PostgreSQL |

---

## 🚀 Quick Start

### Prerequisites

- **OS:** WSL2 Ubuntu 24.04 LTS (or any Linux)
- **Python:** 3.12+
- **Docker:** 29.2.1+
- **GPU:** NVIDIA GPU with CUDA (for Whisper transcription)
- **RAM:** 8GB minimum (16GB recommended)

### Installation

#### 1. Clone Repository

```bash
git clone https://github.com/iamisam/clara-automation.git
cd clara-automation
```

#### 2. Install uv (Python Package Manager)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

#### 3. Install Python Dependencies

```bash
uv venv
source .venv/bin/activate
uv sync
```

#### 4. Install Ollama + Llama 3

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull Llama 3 model
ollama pull llama3
```

#### 5. Setup Environment Variables

```bash
cp .env.example .env
```

Edit `.env`:

```bash
DATASET_PATH=./dataset
OUTPUT_PATH=./outputs

# Model Settings
WHISPER_MODEL=small
OLLAMA_MODEL=llama3

# GPU Settings
CUDA_DEVICE=0
WHISPER_COMPUTE_TYPE=float16

# Constraints
ANONYMIZE_OUTPUT=false
```

#### 6. Start Docker Services (n8n)

```bash
docker-compose up -d
```

Wait 30 seconds for n8n to start, then access: http://localhost:5678

#### 7. Import n8n Workflow

1. Open n8n: http://localhost:5678
2. Click **Settings** → **Import from file**
3. Select `workflows/clara_workflow.json`

#### 8. Start API Wrapper

```bash
# In a separate terminal
source .venv/bin/activate
python3 api_wrapper.py
```

API running on http://localhost:5000

---

## 📂 File Structure

### Required Dataset Structure

```
dataset/
├── demo/
│   ├── account_001/
│   │   └── demo_call.txt
│   ├── account_002/
│   │   └── recording.m4a
│   └── ben_electric/
│       └── transcript.txt
│
└── onboarding/
    ├── account_001/
    │   └── onboarding_call.m4a
    └── ben_electric/
        ├── audio1975518882.m4a
        └── chat.txt
```

**Rules:**
- Demo calls: `dataset/demo/<account_id>/<any_filename>.[txt|m4a|mp4]`
- Onboarding calls: `dataset/onboarding/<account_id>/<any_filename>.[txt|m4a|mp4]`
- Account ID from folder name links demo → onboarding

### Output Structure

```
outputs/
└── accounts/
    └── <account_id>/
        ├── v1/
        │   ├── v1.json              # Account memo from demo
        │   └── agent_spec.json      # Retell agent config v1
        ├── v2/
        │   ├── v2.json              # Updated account memo
        │   └── agent_spec.json      # Retell agent config v2
        └── changelog.txt            # v1 → v2 changes
```

---

## 🎬 Usage

### Method 1: Using n8n Workflow (Recommended)

1. Place your files in `dataset/` following the structure above
2. Open n8n: http://localhost:5678
3. Open the imported "clara_workflow"
4. Click **"Execute workflow"**
5. Check outputs in `outputs/accounts/`

### Method 2: Direct API Call

```bash
# Discover all processable files
curl http://localhost:5000/discover

# Process all discovered files
curl -X POST http://localhost:5000/batch

# Process single file
curl -X POST http://localhost:5000/process \
  -H "Content-Type: application/json" \
  -d '{
    "file": "dataset/demo/ben_electric/transcript.txt",
    "account_id": "ben_electric",
    "type": "demo"
  }'
```
## 📊 Diff Viewer Dashboard

### Running Locally

```bash
streamlit run scripts/streamlit_diff_viewer.py
```

Access: http://localhost:8501

**Password:** `clara2026automation`

### Live Demo

🔗 **https://clara-automation-67.streamlit.app**

**Credentials:**
- Password: `clara2026automation`

**Features:**
- Side-by-side v1 vs v2 comparison
- Highlighted changes
- Changelog summary
- Download agent specs as JSON

---

## 🎥 Video Demo

📹 **Loom Video:** [https://www.loom.com/share/your-video-id]

**Demo covers:**
1. File structure setup
2. Running batch processing via n8n
3. Outputs examination (v1, v2, changelog)
4. Streamlit diff viewer walkthrough

---

## 🐛 Troubleshooting

### Issue: n8n can't reach API

**Solution:** Update workflow HTTP Request URL to your machine's IP:

```bash
# Get your IP
ip addr show eth0 | grep "inet " | awk '{print $2}' | cut -d/ -f1

# Update n8n workflow URL to:
http://YOUR_IP:5000/batch
```

### Issue: Whisper transcription fails

**Solution:** Check GPU availability:

```bash
nvidia-smi

# If no GPU, use CPU mode in .env:
CUDA_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

### Issue: Ollama not responding

**Solution:** Verify Ollama is running:

```bash
ollama list
ollama serve  # Start Ollama service
```

### Issue: LLM returns invalid JSON

**Known limitation:** Llama 3 sometimes adds preambles. The code includes regex cleanup:

```python
match = re.search(r'\{.*\}', response, re.DOTALL)
data = json.loads(match.group())
```

For better results, consider using Claude API (Anthropic) instead of Ollama.

---

## 🚧 Known Limitations

1. **LLM Hallucinations:** Llama 3 occasionally invents data. Manual review recommended.
2. **No Retell API Integration:** Agent specs must be manually imported to Retell UI.
3. **No Task Tracker:** GitHub Issues integration prepared but not implemented.
4. **No Database:** Uses filesystem storage (Supabase integration skipped for simplicity).

---

## 🔮 Future Improvements

- [ ] Add Retell API integration for automatic agent creation
- [ ] Implement Supabase for structured storage
- [ ] Add GitHub Actions for CI/CD
- [ ] Support email/calendar integration
- [ ] Multi-language support
- [ ] Confidence scoring for extractions

---

## 📦 Dependencies

**Core:**
- `faster-whisper==1.2.1` - Audio transcription
- `ollama==0.6.1` - LLM client
- `flask==3.1.3` - API wrapper
- `streamlit==1.55.0` - Dashboard UI
- `python-dotenv==1.2.2` - Environment management

**ML/AI:**
- `torch==2.6.0+cu124` - PyTorch with CUDA
- `torchaudio==2.6.0+cu124` - Audio processing
- `torchvision==0.21.0+cu124` - Vision utilities

**Full list:** See `pyproject.toml`

---

## 👤 Author

**Your Name**
- GitHub: [@iamisam](https://github.com/iamisam)
- Repository: [clara-automation](https://github.com/iamisam/clara-automation)

---
