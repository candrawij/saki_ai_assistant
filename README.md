# 🤖 Saki - Personal AI Assistant

**v4.5** - Memory Intelligence Edition

![Status](https://img.shields.io/badge/Status-Hobby%20Project-yellow)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.58-red)

---

## 📋 WHAT'S NEW

### v4.5 Updates (Just Added)
- ✨ **Dotenv Integration** - Secure environment variable management
- ✨ **Memory Intelligence** - Importance scoring, access tracking
- ✨ **Duplicate Detection** - AI finds and merges similar facts
- ✨ **Health Dashboard** - Memory quality analysis
- ✨ **Comprehensive Audit** - See `AUDIT_REPORT.md`

---

## 🎯 FEATURES

### 💬 Chat
- Talk to Saki naturally
- Auto-extract important facts
- Maintain conversation history
- Context-aware responses

### 📚 Memory System
- Store facts with importance scoring (1-10)
- Track access count and last accessed time
- Manual & auto-extracted facts
- Category organization

### 🧠 Intelligence Dashboard
- Memory health metrics
- Duplicate detection with AI
- Access pattern analysis
- Importance-based sorting

### 📄 Document Management
- Upload PDF, DOCX, TXT, MD
- Semantic search with Chroma
- Auto-summarization
- Q&A on documents

### 📤 Export/Import
- Backup memory as JSON
- Import from other sources
- Data portability

---

## ⚙️ SETUP

### Prerequisites
- Python 3.8+
- [Ollama](https://ollama.ai) running locally
- Windows/Linux/Mac

### Installation

1. **Clone/Extract Project**
```bash
cd "e:\Priv Bot"
```

2. **Setup Environment**
```bash
# Create .env file (copy from .env.example)
copy .env.example .env
# Edit .env with your settings
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
# OR for clean minimal:
pip install -r requirements-clean.txt
```

4. **Start Ollama**
```bash
ollama serve
# In another terminal:
ollama pull qwen3:4b
ollama pull nomic-embed-text
```

5. **Run Saki**
```bash
streamlit run saki_server.py
```

6. **Access**
- Open http://localhost:8501
- Login with password (default: `saki2024`)

---

## 📁 PROJECT STRUCTURE

```
e:\Priv Bot\
├── saki_server.py              # Main application
├── requirements.txt            # All dependencies
├── requirements-clean.txt      # Minimal dependencies
├── .env.example                # Configuration template
│
├── AUDIT_REPORT.md            # ✨ Detailed audit (300+ lines)
├── IMPROVEMENT_GUIDE.md       # ✨ Code fixes & examples
├── SUMMARY.md                 # ✨ Executive summary
├── README.md                  # This file
│
├── saki_memory.db             # SQLite database
├── chroma_db/                 # Vector database for docs
├── documents/                 # Uploaded documents
├── ringkasan/                 # Saved summaries
├── exports/                   # Memory exports
└── logs/                      # Application logs
```

---

## 📚 DOCUMENTATION

### Important Files
- **[AUDIT_REPORT.md](./AUDIT_REPORT.md)** - Comprehensive security & quality audit (14 issues found)
- **[IMPROVEMENT_GUIDE.md](./IMPROVEMENT_GUIDE.md)** - Code examples for fixes
- **[SUMMARY.md](./SUMMARY.md)** - Executive summary & next steps

### Configuration
See `.env.example` for all available options:
```env
ADMIN_PASSWORD=saki2024
MODEL=qwen3:4b
OLLAMA_URL=http://localhost:11434
```

---

## ⚠️ IMPORTANT NOTES

### Current Status: ⚠️ BETA
This project is in **hobby project** stage. It works well for personal use but has several issues for production:

**Critical Issues Found (see AUDIT_REPORT.md):**
1. ❌ No proper exception handling
2. ❌ No logging system
3. ❌ No input validation
4. ❌ Database connection issues
5. ❌ No Ollama retry logic

**Recommended Fixes:** See [IMPROVEMENT_GUIDE.md](./IMPROVEMENT_GUIDE.md) for code examples.

### Limitations
- **SQLite only** - Not concurrent-write safe
- **Local AI only** - Requires Ollama running
- **Memory size** - Works well up to ~10K facts
- **No backup** - Implement your own backup strategy

---

## 🚀 QUICK IMPROVEMENTS (1 Weekend Project)

**High-impact fixes you can do in ~4 hours:**

1. Add logging (1 hour)
2. Fix exception handling (1 hour)
3. Add input validation (1 hour)
4. DB context manager (1 hour)

See **[IMPROVEMENT_GUIDE.md](./IMPROVEMENT_GUIDE.md#implementation-priority)** for code.

---

## 🤝 USAGE TIPS

### Effective Memory Usage
1. **Be specific** - "I like Python" vs "I prefer Python for backend because of FastAPI"
2. **Use categories** - Helps organize facts
3. **Review Intelligence** - Check for duplicates monthly
4. **Clean up** - Delete low-importance facts

### Performance Tips
- Keep facts < 10,000 total for fast searches
- Summarize long documents first
- Don't upload huge PDFs (> 100MB)
- Regularly export memory backup

---

## 📊 AUDIT SUMMARY

**Project Rating: 6/10**

| Category | Score | Notes |
|----------|-------|-------|
| Features | 8/10 | Many interesting features |
| Code Quality | 4/10 | Needs better error handling |
| Security | 4/10 | Missing validation & rate limiting |
| Performance | 5/10 | SQLite bottleneck |
| Documentation | 7/10 | Good with audit added |
| **Overall** | **6/10** | Good hobby project |

See [AUDIT_REPORT.md](./AUDIT_REPORT.md) for full details.

---

## 🐛 KNOWN ISSUES

| Issue | Workaround | Priority |
|-------|-----------|----------|
| Bare except blocks | See IMPROVEMENT_GUIDE.md | CRITICAL |
| No logging | Difficult to debug | HIGH |
| SQLite concurrency | Single user only | MEDIUM |
| No input validation | Avoid special characters | MEDIUM |
| Datetime parsing | Works for standard formats | LOW |

---

## 🔒 SECURITY NOTES

- ⚠️ **Store password securely** - Use strong password in `.env`
- ⚠️ **No encryption** - Database not encrypted
- ⚠️ **No backups** - Implement backup strategy
- ⚠️ **Local only** - Not designed for network sharing
- ✅ **Uses parameterized queries** - Protected from SQL injection
- ✅ **Environment variables** - Secrets not in code

**Recommendations:**
- Use strong password (20+ chars)
- Regular backups to safe location
- Don't expose on internet without auth layer
- Consider encryption for sensitive data

---

## 🛠️ DEVELOPMENT

### Running Tests
```bash
pytest tests/
```

### Adding Features
1. Update database schema in `init_db()`
2. Add functions for new logic
3. Update Streamlit UI
4. Add to Intelligence dashboard if relevant

### Code Standards
- Use type hints
- Add logging for important events
- Handle exceptions explicitly
- Validate all input

---

## 📝 CHANGELOG

### v4.5 (June 2026)
- ✨ Added Memory Intelligence dashboard
- ✨ Importance scoring system
- ✨ Access tracking
- ✨ Duplicate detection
- ✨ Dotenv integration
- 📋 Comprehensive audit & improvement guide

### v4.0
- 💬 Chat functionality
- 📚 Memory system
- 📄 Document management
- 🧠 Auto-extraction

---

## 🎓 LEARNING RESOURCES

**For improving this project:**
- [Python Error Handling](https://docs.python.org/3/tutorial/errors.html)
- [Python Logging](https://docs.python.org/3/library/logging.html)
- [SQLite Best Practices](https://www.sqlite.org/bestpractice.html)
- [Type Hints](https://docs.python.org/3/library/typing.html)

---

## 📞 SUPPORT

**Issues:**
- Check [AUDIT_REPORT.md](./AUDIT_REPORT.md) for known issues
- See [IMPROVEMENT_GUIDE.md](./IMPROVEMENT_GUIDE.md) for fixes
- Review logs in `logs/saki.log`

**Questions:**
- Check documentation files
- Review example configurations

---

## 📄 LICENSE

Personal hobby project. Use freely for your own purposes.

---

## 🙏 CREDITS

- **Ollama** - Local LLM engine
- **Streamlit** - Web UI framework
- **Chroma** - Vector database
- **ChromaDB** - Semantic search

---

**Last Updated:** June 3, 2026  
**Audit Status:** ✅ Complete - See [AUDIT_REPORT.md](./AUDIT_REPORT.md)  
**Current Version:** v4.5 + Audit Edition

---

## 🚀 NEXT STEPS

1. ✅ Review [AUDIT_REPORT.md](./AUDIT_REPORT.md)
2. ✅ Study [IMPROVEMENT_GUIDE.md](./IMPROVEMENT_GUIDE.md)
3. 🔨 Implement Priority 1 fixes (2-3 hours)
4. ✅ Add logging & better error handling
5. ✅ Test thoroughly
6. 📊 Monitor with logs

**Estimated improvement time: 30-40 hours → Score 8/10**

Selamat menggunakan Saki! 🎉
