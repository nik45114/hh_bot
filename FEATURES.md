# 🤖 HH Job Bot - Feature Overview

## 🎯 Core Features

### 1. Automated Job Application
- **Full OAuth Integration**: Connects to HH.ru API with OAuth 2.0 token
- **Smart Application**: Automatically applies to matching vacancies
- **Cover Letter Generation**: AI-powered personalized cover letters using OpenAI GPT-4
- **Error Handling**: Graceful handling of API limits, network errors, invalid credentials

### 2. Flexible Search Criteria
**Industry Selection:**
- 💻 IT Specialists
- 💼 Management Roles (Руководители)
- 🔧 Other/Custom

**Location Options:**
- Popular cities: Moscow, Saint Petersburg, Ekaterinburg, etc.
- All Russia option
- Custom city input

**Work Format:**
- 🏠 Remote-only toggle
- On-site, hybrid, flexible schedules
- Full-time, part-time, project-based

**Advanced Filters:**
- 💰 Minimum salary requirement
- 📝 Multiple keywords (comma-separated)
- 👔 Management level (Team Lead, Director, Product Manager, etc.)
- 📅 Experience level (no experience, 1-3 years, 3-6 years, 6+ years)

### 3. Intelligent Prompt Management
**Built-in Templates:**
- **IT Prompt**: Focuses on technical skills, technologies, development experience
- **Management Prompt**: Emphasizes leadership, KPIs, team building, strategic thinking
- **Universal Prompt**: Generic template for other roles

**Customization:**
- ✏️ Edit prompts directly in Telegram
- 🔄 Reset to default anytime
- 📝 Preview first 200 characters
- 🎨 Supports placeholders: {vacancy_title}, {company_name}, {skills}, etc.

### 4. Dual Application Modes
**Auto-Apply Mode (🤖 ON):**
- Bot automatically applies to ALL found vacancies
- Generates custom cover letter for each
- Shows results with success/failure status
- Ideal for bulk application

**Manual Mode (🤖 OFF):**
- Shows vacancy card with details
- Interactive buttons: [Apply] [Skip] [Open on Site]
- User controls each application
- Better for selective application

### 5. Comprehensive Statistics
**Tracking:**
- 📊 Daily application count
- 📈 Total applications across all time
- 📝 Recent application history (last 5)
- ✅/❌ Success/failure status per application

**History:**
- Vacancy title and company name
- Application date
- Status (success/failed/pending)
- Error messages if failed

### 6. Rich User Interface
**Main Menu:**
```
🔍 Поиск вакансий      - Start job search
⚙️ Настроить критерии  - Configure search criteria
✍️ Промпт сопровода    - Manage cover letter prompts
🤖 Авто-отклик: ✅/❌   - Toggle auto-apply
📊 Статистика         - View application stats
ℹ️ Помощь            - Help and setup guide
```

**Vacancy Card (Manual Mode):**
```
📋 Вакансия 1 из 5

📋 Senior Product Manager (Remote)

🏢 Компания: Tech Innovations Ltd
💰 150,000 - 250,000 RUB
🔗 https://hh.ru/vacancy/123456

[✅ Откликнуться] [❌ Пропустить] [🔗 Открыть на сайте]
```

### 7. Bot Commands
| Command | Description |
|---------|-------------|
| `/start` | Show main menu |
| `/criteria` | Open criteria settings |
| `/search` | Start immediate job search |
| `/prompt` | Manage cover letter prompt |
| `/apply_on` | Enable auto-apply mode |
| `/apply_off` | Disable auto-apply mode |
| `/stats` | View application statistics |
| `/help` | Show help and setup instructions |
| `/cancel` | Cancel current text input |

## 🔧 Technical Features

### Database (SQLite)
**Tables:**
- `users` - User profiles (chat_id, username, timestamps)
- `preferences` - Search criteria per user (domain, location, keywords, salary, etc.)
- `applications` - Application history (vacancy_id, title, company, cover_letter, status)
- `processed_vacancies` - Prevents showing same vacancy twice

**Features:**
- Automatic schema initialization
- Transaction safety with context managers
- Foreign key constraints
- Indexed queries for performance

### HH.ru API Integration
**Endpoints Used:**
- `GET /vacancies` - Search with filters
- `GET /vacancies/{id}` - Get vacancy details
- `POST /negotiations` - Apply to vacancy
- `GET /resumes/mine` - List user's resumes

**Error Handling:**
- HTTP 400: Invalid request → User-friendly error
- HTTP 403: Insufficient permissions → Token check prompt
- HTTP 429: Rate limit → Wait and retry suggestion
- Timeouts: Graceful degradation with retry logic

### Security
**✅ CodeQL Scan: 0 Vulnerabilities**
- No hardcoded secrets (all via environment)
- SQL injection prevention (parameterized queries)
- User access control (ALLOWED_USER_ID option)
- Secure token storage in .env

### Configuration
**Environment Variables (.env):**
```bash
# Required
TELEGRAM_BOT_TOKEN=xxx
OPENAI_API_KEY=xxx
HH_ACCESS_TOKEN=xxx
HH_RESUME_ID=xxx

# Optional
ALLOWED_USER_ID=xxx
SEARCH_KEYWORDS=keyword1,keyword2
MAX_APPLICATIONS_PER_DAY=20
DEFAULT_AREA=1
DEFAULT_SCHEDULE=remote
MIN_SALARY=0
```

## 📊 Usage Statistics

### Bot Metrics
- **822 lines** in main bot file
- **9 commands** implemented
- **6 main menu actions**
- **8 criteria options**
- **3 prompt templates**

### Database Metrics
- **4 tables** with relationships
- **Auto-increment** IDs for applications
- **Timestamps** on all records
- **JSON** storage for complex types

### API Integration
- **OAuth 2.0** authentication
- **Retry logic** for failed requests
- **Timeout** handling (10s default)
- **Rate limit** awareness

## 🎨 UI/UX Features

### Visual Indicators
- ✅ Success / Enabled
- ❌ Error / Disabled
- 🔍 Searching
- ⏳ Loading
- 💻 IT Domain
- 💼 Management
- 🏠 Remote work
- 💰 Salary

### User Experience
- **Inline keyboards** for all interactions
- **Back button** on every submenu
- **Progress indicators** for long operations
- **Confirmation messages** for updates
- **Preview** for long text (200 chars)
- **Numbered** vacancy cards (1 of 5)
- **Cancel option** for text inputs

## 🌟 Advanced Features

### Smart Cover Letter Generation
**Context-Aware:**
- Adapts to IT vs Management roles
- Considers remote/on-site position
- Highlights relevant experience
- Matches job requirements

**Quality:**
- 150-250 words (professional length)
- No generic phrases
- Specific achievements and metrics
- Call to action

### Application Tracking
**Prevents Duplicates:**
- Tracks processed vacancy IDs
- Won't show same vacancy twice
- Per-user tracking (multi-user support)

**Historical Data:**
- When applied
- Success/failure status
- Error messages stored
- Cover letter saved

### Error Recovery
**Graceful Degradation:**
- OpenAI unavailable → Simple cover letter fallback
- HH API down → Clear error message
- Missing token → Setup instructions
- Invalid input → Validation with retry

## 🚀 Deployment Features

### Production Ready
- **systemd service** example included
- **Logging** to file and console (INFO/WARNING/ERROR)
- **Restart-safe** (database persists state)
- **Environment-based** config
- **No hardcoded** values

### Monitoring
- **Log files**: bot.log, applications.log
- **Console output**: Real-time status
- **Timestamps**: All database records
- **Error tracking**: Logged with context

## 📚 Documentation

### Included Docs
1. **README.md** - Setup and usage guide
2. **IMPLEMENTATION_SUMMARY.md** - Technical details
3. **UX_FLOWS.md** - User interaction flows
4. **FEATURES.md** (this file) - Feature overview
5. **.env.example** - Configuration template

### Help System
- `/help` command with inline instructions
- OAuth token acquisition guide
- Resume ID retrieval steps
- Troubleshooting tips
- API documentation links

## 🎯 Use Cases

### Use Case 1: Active Job Seeker
**Scenario:** User looking for management position, remote only, 150k+ salary

**Flow:**
1. Set criteria: Management, Remote, Moscow, 150k
2. Customize prompt for leadership focus
3. Enable auto-apply
4. Run daily searches
5. Review stats

### Use Case 2: Selective Applicant
**Scenario:** User wants to review each vacancy before applying

**Flow:**
1. Set criteria: IT, Python, 100k+
2. Keep auto-apply OFF
3. Run search
4. Review each vacancy card
5. Click [Apply] or [Skip] per vacancy

### Use Case 3: Multi-Domain Search
**Scenario:** User open to both IT and Management roles

**Flow:**
1. Search once with IT criteria
2. Switch to Management domain
3. Search again
4. Bot tracks all applications
5. View combined stats

## 🔄 Future Enhancement Ideas

**Potential Additions:**
- [ ] Multiple resume support (switch between resumes)
- [ ] Token auto-refresh (using refresh_token)
- [ ] Scheduled searches (cron-like)
- [ ] Company blacklist (skip certain companies)
- [ ] Notification channels (push notifications for new matches)
- [ ] Advanced filters (company size, industry, etc.)
- [ ] Application drafts (save before sending)
- [ ] Cover letter templates library
- [ ] Integration with other job boards
- [ ] Analytics dashboard (web interface)

## 📞 Support

**Resources:**
- GitHub: https://github.com/nik45114/hh_bot
- HH API Docs: https://github.com/hhru/api
- Telegram Bot API: https://core.telegram.org/bots/api

**Contact:**
- Issues: GitHub Issues
- Author: @nik45114

---

**Built with:** Python, python-telegram-bot, OpenAI API, SQLite, HH.ru API
**License:** MIT
**Version:** 2.0 (Enhanced)
