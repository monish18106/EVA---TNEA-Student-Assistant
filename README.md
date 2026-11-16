# EVA – TNEA AI Assistant 🎓

An intelligent AI-powered assistant for Tamil Nadu Engineering Admissions (TNEA) using **Retrieval-Augmented Generation (RAG) + LLM architecture** on **2024 cutoff data**.

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Flask](https://img.shields.io/badge/Flask-2.3+-green)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Latest-purple)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ✨ Features

- 🎯 **Smart Query Routing** – Understands 6 different query types
- 🗂️ **College Listings** – Find colleges by district
- 📊 **Cutoff Information** – Get cutoff marks by course , category, district
- 🔍 **Eligibility Checker** – "I scored 185, can I get CSE in Madurai?"
- 💬 **Conversational AI** – Multi-turn conversations with context awareness
- 🛡️ **Zero Hallucinations** – Strict RAG architecture, only uses official data
- ⚡ **Fast & Accurate** – ChromaDB vector search + LLaMA 3.1 8B LLM
- 📱 **Responsive UI** – Works on desktop, tablet, mobile

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│           User Interface (Web Browser)          │
│   HTML5 + CSS3 + Vanilla JavaScript             │
└─────────────┬───────────────────────────────────┘
              │
              ↓
┌─────────────────────────────────────────────────┐
│        Flask Backend (Python)                   │
│   • Session Management                          │
│   • Query Routing (6 types)                     │
│   • Context Merging                             │
└─────────────┬───────────────────────────────────┘
              │
    ┌─────────┴─────────┐
    ↓                   ↓
┌─────────────┐   ┌──────────────┐
│    RAG      │   │   LLM API    │
│ ChromaDB    │   │ Groq LLaMA   │
│             │   │ 3.1 8B       │
└─────────────┘   └──────────────┘
    ↓
┌─────────────────────────────────────┐
│   Vector Database                   │
│   • college_catalog_db              │
│   • cutoff_db                       │
│   • query_history_db                |
|   embeddings model                  |
|   all-MiniLM-L6-v2                  │
└─────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip (Python package manager)
- Groq API key (free from https://console.groq.com)

### 1️⃣ Clone Repository

```bash
git clone https://github.com/yourusername/eva-tnea.git
cd eva-tnea
```

### 2️⃣ Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Setup Environment Variables

```bash
# Copy example file
cp .env.example .env

# Edit .env and add your Groq API key
# Windows: notepad .env
# Mac/Linux: nano .env
```

**Add your credentials to `.env`:**
```
GROQ_API_KEY=sk_your_groq_api_key_here
FLASK_ENV=production
FLASK_SECRET_KEY=your-random-secret-key
```

**Get Groq API Key:**
1. Visit [Groq Console](https://console.groq.com)
2. Sign up or login
3. Create new API key
4. Copy and paste into `.env`

### 5️⃣ Run Application

```bash
python app.py
```

You should see:
```
 * Running on http://127.0.0.1:5000
 * Press CTRL+C to quit
```

### 6️⃣ Open in Browser

Visit: **http://localhost:5000**

---

## 📝 Usage Examples

### Example 1: Find Colleges by District
```
User: "colleges in madurai"
EVA: Shows all engineering colleges in Madurai district
```

### Example 2: Find Colleges Offering Specific Course
```
User: "colleges in coimbatore offering cse"
EVA: Returns colleges in Coimbatore offering Computer Science Engineering
```

### Example 3: Check Cutoff Marks
```
User: "cutoff for cse in salem mbc"
EVA: CSE cutoff marks for MBC category in Salem:
     • Thiagarajar College of Engineering: 163.0
     • Anna University Regional Campus: 146.0
```

### Example 4: Check Your Eligibility
```
User: "i scored 185 can i get cse mbc in madurai"
EVA: Analyzes your score + cutoff data
     • Safe options: Anna University Regional Campus (cutoff 146)
     • Moderate risk: Thiagarajar College (cutoff 163)
     • Recommendation: Apply to both
```

### Example 5: Compare Queries
```
User: "colleges in madurai"
[Results shown]
User: "now compare with salem"
EVA: Compares colleges in Madurai vs Salem
```

### Example 6: General Questions
```
User: "what is computer science engineering"
EVA: [Explains using LLM]
```

---

## 📋 Query Types Supported

| Type | Description | Example |
|------|-------------|---------|
| **Type 1** | Colleges by district | "colleges in madurai" |
| **Type 2** | Colleges offering course | "colleges in cbe offering cse" |
| **Type 3** | Cutoff information | "cutoff for cse in salem mbc" |
| **Type 4** | Comparison | "compare both", "which is better" |
| **Type 5** | Eligibility check | "i scored 185 can i get cse mbc" |
| **Type 6** | General knowledge | "what is engineering", "hello" |

---

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend** | Flask (Python) | Web server & API |
| **Database** | ChromaDB | Vector database for RAG |
| **LLM** | Groq API (LLaMA 3.1 8B) | General Q&A & analysis |
| **Frontend** | HTML5, CSS3, Vanilla JS | Web interface |
| **API** | RESTful | Client-server communication |

---

## 📚 Project Structure

```
eva-tnea/
├── app.py                    # Flask web server
├── rag_pipeline.py           # Query processing & RAG logic
├── llm_api.py                # Groq LLM integration
├── requirements.txt          # Python dependencies
│
├── templates/
│   └── index.html            # Web UI template
│
├── static/
│   ├── app.js                # Frontend JavaScript
│   └── style.css             # UI styling
│
├── prompts/
│   └── system_prompt.txt     # LLM system instructions
│
├── vector_db/                # ChromaDB database
│   ├── chroma.sqlite3
│   └── [college & cutoff data]
│
├── .env.example              # Environment template
├── .gitignore                # Git ignore rules
└── README.md                 # This file
```

---

## 🔧 Configuration

### Environment Variables (`.env`)

```
# Groq API Key (Required)
GROQ_API_KEY=sk_xxxxxxxxxxxxxxxxxxxxx

# Flask Configuration
FLASK_ENV=production                    # or 'development'
FLASK_SECRET_KEY=your-secret-key-here   # Change to secure value

# Optional
VECTOR_DB_PATH=./vector_db
MAX_HISTORY=20
```

### Application Settings

Edit values in code if needed:
- **Max conversation history**: `MAX_HISTORY = 20` in `app.py`
- **Max input length**: `maxlength="500"` in `templates/index.html`
- **LLM temperature**: `temperature: 0.7` in `llm_api.py`

---

## 🔐 Security

⚠️ **Important Security Notes:**

1. **Never commit `.env`** – It contains your API key
   - `.env` is automatically ignored (see `.gitignore`)
   - Only `.env.example` is committed

2. **Keep API key secret**
   - Don't share your Groq API key
   - Don't expose it in logs or error messages

3. **Use strong Flask secret key**
   - Generate random string: `python -c "import secrets; print(secrets.token_hex(32))"`

4. **In production**
   - Set `FLASK_ENV=production`
   - Use HTTPS
   - Enable rate limiting (optional)

---

## 🐛 Troubleshooting

### Issue: "GROQ_API_KEY not set"
**Solution:** 
- Ensure `.env` file exists
- Check API key is correct in `.env`
- Restart Flask app after adding API key

### Issue: "chromadb not found"
**Solution:**
```bash
pip install chromadb
pip install -r requirements.txt
```

### Issue: Port 5000 already in use
**Solution:**
```bash
# Use different port
python -c "from app import app; app.run(port=5001)"
```

### Issue: Slow responses
**Solution:**
- First query is slower (model loading)
- Subsequent queries are fast
- Check internet connection
- Verify API rate limits

---

## 📊 Data Source & Collection

This project uses **TNEA 2024 official cutoff data**:
- ✅ Tamil Nadu Engineering Admissions Board (TNEA)
- ✅ 2024 cutoff marks & college listings
- ✅ All districts in Tamil Nadu
- ✅ All engineering courses

**Data Preparation:**
- Initial data sourced from TNEA official sources (partial/scraped)
- Manual data completion & validation performed
- All missing values filled through official references
- Verified against TNEA counselling documents
- Quality-checked for accuracy & consistency

**Data Accuracy:**
- Always verify with official TNEA website
- Data may change; re-check before counselling
- This tool is **advisory only**
- 500+ colleges & cutoff entries manually validated

---

## 💡 Features & Capabilities

### What EVA Can Do ✅

- ✅ List colleges by district
- ✅ Show colleges offering specific courses
- ✅ Provide official cutoff marks
- ✅ Check eligibility based on score
- ✅ Compare different queries
- ✅ Answer general engineering questions
- ✅ Handle typos & abbreviations
- ✅ Remember conversation context

### What EVA Cannot Do ❌

- ❌ Predict future cutoffs
- ❌ Guarantee admission
- ❌ Provide counselling advice
- ❌ Modify official data
- ❌ Accept new cutoff data (2024 only)

---

## 🚀 Deployment

### Local Development
```bash
python app.py
```

### Production (Heroku)

1. Create `Procfile`:
```
web: gunicorn app:app
```

2. Add to `requirements.txt`:
```
gunicorn==21.2.0
```

3. Deploy:
```bash
git push heroku main
heroku config:set GROQ_API_KEY=sk_xxxxx
heroku open
```

### Production (Other Platforms)

Similar steps for Railway, Render, AWS, etc. Ensure:
- ✅ Set environment variables
- ✅ Use production Flask settings
- ✅ Enable HTTPS

---

## 📈 Performance Metrics

| Metric | Value |
|--------|-------|
| Average response time | 1-3 seconds |
| First query latency | 3-5 seconds (model load) |
| Database queries | < 100ms |
| Max conversation history | 20 messages |
| Max input length | 500 characters |

---

## 🤝 Contributing

Want to contribute? Great!

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make changes
4. Test thoroughly
5. Commit: `git commit -m "Add feature description"`
6. Push: `git push origin feature/your-feature`
7. Open a Pull Request

---

## 📝 License

MIT License – See LICENSE file for details

Free to use, modify, and distribute for personal and educational purposes.

---

## ⚠️ Disclaimer

**This project is for educational purposes.**

- Not affiliated with TNEA or Tamil Nadu government
- Data is provided as-is without warranty
- Always verify information from official TNEA sources
- Developers are not responsible for admission decisions
- Use at your own risk

---

## 📞 Support

- **Issues**: Open a GitHub issue with details
- **Questions**: Check existing issues first
- **Data corrections**: Report via GitHub issues

---

## 🎯 Roadmap

### Completed ✅
- [x] 6 query type detection
- [x] RAG architecture with ChromaDB
- [x] LLM integration (Groq)
- [x] Eligibility checking
- [x] Multi-turn conversations
- [x] Web UI

### Planned 🔄
- [ ] Previous year data (2022, 2023)
- [ ] Chat history export
- [ ] Mobile app
- [ ] Offline mode
- [ ] Advanced analytics

---

## 📊 Project Stats

- **Lines of Code**: ~2000+
- **Python Files**: 3 core + 2 config
- **Database Size**: ~50MB+
- **Supported Districts**: 25+
- **Supported Courses**: 35+
- **Categories**: 7 (BC, OC, MBC, BCM, SC, SCA, ST)
- **Colleges**: 500+

---

## 🙏 Acknowledgments

- Groq API for LLaMA 3.1 8B access
- ChromaDB for vector database
- Flask for web framework
- TNEA for official data

---

## 📅 Latest Updates

**Last Updated:** May 2026
- ✅ 2024 TNEA data integrated
- ✅ All 6 query types implemented
- ✅ Production-ready release

---

**Made with ❤️ for Tamil Nadu Engineering Aspirants**

**⭐ If you find this helpful, please star the repository!**
