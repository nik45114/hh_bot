# Implementation Summary: 24/7 Monitoring and Admin Features

## Overview

This update implements comprehensive 24/7 vacancy monitoring, administrative features, and improved reliability for the HH Job Bot.

## Features Implemented

### 1. 24/7 Vacancy Monitoring

**Description**: Automated background job that continuously checks for new vacancies based on user criteria.

**Components**:
- APScheduler integration for periodic task execution
- Configurable check interval (default: 3 minutes, configurable via `HH_SEARCH_INTERVAL_SEC`)
- Per-user monitoring state management in database
- Automatic deduplication to avoid showing same vacancies twice
- Integration with auto-apply feature for automatic job applications

**Database Tables Added**:
- `sent_vacancies`: Tracks which vacancies have been sent to users
- `monitoring_state`: Stores monitoring status and last check timestamp per user

**User Controls**:
- Toggle via main menu button: "📡 Мониторинг 24/7"
- Commands: `/monitoring_on`, `/monitoring_off`
- Shows status in `/help` command

**How It Works**:
1. Scheduler runs every N seconds (configurable)
2. Fetches list of users with monitoring enabled
3. For each user, searches vacancies based on their criteria
4. Filters out already-sent vacancies using deduplication
5. Sends new vacancies to user (with auto-apply if enabled)
6. Updates last check timestamp

### 2. Rate Limiting and Retry Logic

**Description**: Robust handling of HH.ru API rate limits and transient failures.

**Features**:
- Exponential backoff retry mechanism (max 3 attempts)
- Automatic handling of 429 (Rate Limit) responses
- Respects `Retry-After` headers from API
- Configurable rate limit via `HH_RATE_LIMIT_QPS` (default: 0.5 requests/sec)
- Retry on server errors (5xx) with exponential backoff
- Timeout handling with retries

**Implementation**:
- New `_request_with_retry()` method in `HeadHunterClient`
- All API methods updated to use retry logic
- Logging of retry attempts and wait times

### 3. Administrative Commands

**Description**: Secure admin-only commands for code updates and service management.

**Features**:
- `/update_code`: Updates bot code from Git repository
  - Executes `git fetch --all --prune`
  - Checks for local changes (warns if dirty)
  - Performs `git pull --ff-only origin main`
  - Shows commit changes and recommends restart
  
- `/restart`: Restarts systemd service
  - Requires `ALLOW_SYSTEMCTL=true` in config
  - Executes `sudo systemctl restart <service_name>`
  - Shows service status after restart
  - Requires sudo permissions configured

**Security**:
- Access restricted by `ADMIN_CHAT_IDS` environment variable
- Commands only available to listed admin user IDs
- All actions logged
- Errors safely reported to admin

**Configuration**:
```env
ADMIN_CHAT_IDS=123456789,987654321
ALLOW_SYSTEMCTL=true
SERVICE_NAME=hh_bot
BOT_INSTALL_PATH=/opt/hh_bot
```

### 4. Enhanced Help System

**Description**: Improved `/help` command showing current bot state.

**Displays**:
- Current auto-apply status (ON/OFF)
- Current monitoring status (ON/OFF)
- All available commands
- Setup instructions for HH.ru API
- Admin commands (if user is admin)
- Configuration examples

### 5. Improved Database Schema

**New Tables**:
```sql
sent_vacancies (
    chat_id INTEGER,
    vacancy_id TEXT,
    sent_at TIMESTAMP,
    PRIMARY KEY (chat_id, vacancy_id)
)

monitoring_state (
    chat_id INTEGER PRIMARY KEY,
    monitoring_enabled BOOLEAN DEFAULT 0,
    last_check TIMESTAMP
)
```

**New Methods**:
- `mark_vacancy_sent(chat_id, vacancy_id)`
- `is_vacancy_sent(chat_id, vacancy_id)`
- `get_monitoring_state(chat_id)`
- `update_monitoring_state(chat_id, enabled, last_check)`
- `get_all_monitoring_users()`

### 6. Configuration Enhancements

**New Environment Variables**:
```env
# Admin settings
ADMIN_CHAT_IDS=your_admin_id_1,your_admin_id_2

# Monitoring settings
HH_SEARCH_INTERVAL_SEC=180  # 3 minutes
HH_RATE_LIMIT_QPS=0.5       # 0.5 requests per second

# System management
ALLOW_SYSTEMCTL=false       # Enable /restart command
SERVICE_NAME=hh_bot         # Service name for restart
BOT_INSTALL_PATH=/opt/hh_bot  # Path for git pull
```

## Testing

### Unit Tests Created

**test_database.py**:
- User creation and retrieval
- Preferences management
- Vacancy deduplication (sent/processed)
- Monitoring state management
- Application logging

**test_hh_client.py**:
- Client initialization
- Vacancy search
- Vacancy details retrieval
- Job application (success and error cases)
- Rate limiting handling
- Exponential backoff retry logic

**test_prompts.py**:
- Prompt generation for different domains
- Prompt structure validation

**Results**: 18 tests, all passing ✅

### Manual Verification

- ✅ Bot imports without errors
- ✅ JobBot instance creation successful
- ✅ Database initialization working
- ✅ Scheduler initialization working
- ✅ Configuration loading correctly

## Documentation Updates

### README.md

- Added 24/7 monitoring to features list
- Added `/monitoring_on` and `/monitoring_off` commands
- Added admin commands documentation
- Added section on 24/7 monitoring with how-it-works
- Added admin functions setup guide
- Added sudo configuration instructions

### .env.example

- Added all new configuration variables
- Added comments explaining each setting
- Added admin settings section
- Added monitoring settings section
- Added system management settings section

## Deployment Notes

### For Production Use

1. **Set Admin IDs**:
   ```env
   ADMIN_CHAT_IDS=your_telegram_user_id
   ```

2. **Configure Monitoring Interval**:
   ```env
   HH_SEARCH_INTERVAL_SEC=180  # Adjust based on needs
   ```

3. **For Auto-Update Feature**:
   - Ensure bot directory is a git repository
   - Set `BOT_INSTALL_PATH` to actual installation path
   - Bot process must have read/write access to directory

4. **For Service Restart Feature**:
   ```bash
   # Add to /etc/sudoers.d/hh_bot
   bot_user ALL=(ALL) NOPASSWD: /bin/systemctl restart hh_bot
   bot_user ALL=(ALL) NOPASSWD: /bin/systemctl status hh_bot
   ```
   
   Then enable in config:
   ```env
   ALLOW_SYSTEMCTL=true
   ```

### Rate Limiting

- Default: 0.5 requests/second (conservative)
- Adjust based on your HH.ru API quota
- Bot automatically handles 429 responses

### Monitoring Intervals

- Recommended minimum: 180 seconds (3 minutes)
- Too frequent checks may trigger rate limits
- Consider your number of active users

## Architecture Changes

### Before
- Manual search only
- No continuous monitoring
- Basic error handling
- No admin features

### After
- Manual search + 24/7 monitoring
- Automated vacancy discovery
- Robust retry logic with exponential backoff
- Admin code updates and service management
- Enhanced deduplication
- Rate limiting compliance

## Security Considerations

✅ **Implemented**:
- Admin-only commands with ID verification
- All secrets in environment variables
- SQL injection prevention (parameterized queries)
- User access control (ALLOWED_USER_ID)
- Sudo permissions configurable per-command

❗ **Production Recommendations**:
- Use strong bot token
- Restrict admin IDs to trusted users only
- Keep `.env` file secure (not in git)
- Use systemd service isolation
- Regular monitoring of logs
- Keep dependencies updated

## Performance Considerations

- APScheduler runs in same process (async)
- Database uses SQLite (single file, suitable for small-medium scale)
- Rate limiting prevents API abuse
- Exponential backoff reduces thundering herd
- Deduplication prevents duplicate processing

## Backward Compatibility

✅ All existing features preserved:
- Manual search still works
- Old commands still function
- Database schema extended (not modified)
- Existing preferences maintained

## Future Enhancements

Potential additions (not implemented):
- [ ] Multi-resume support
- [ ] Token auto-refresh
- [ ] Company blacklist
- [ ] Advanced filters (company size, industry)
- [ ] Web dashboard
- [ ] Metrics/analytics
- [ ] Notification channels

## Troubleshooting

### Monitoring Not Working
1. Check monitoring is enabled: `/monitoring_on`
2. Verify `HH_SEARCH_INTERVAL_SEC` is set
3. Check logs for errors
4. Ensure HH API credentials are valid

### Rate Limiting Issues
1. Increase `HH_SEARCH_INTERVAL_SEC`
2. Decrease `HH_RATE_LIMIT_QPS`
3. Check number of active monitoring users
4. Review logs for 429 errors

### Admin Commands Not Available
1. Set `ADMIN_CHAT_IDS` in `.env`
2. Get your user ID from @userinfobot
3. Restart bot after config change
4. Check user ID matches config

### Git Update Fails
1. Verify `BOT_INSTALL_PATH` is correct
2. Ensure directory is git repository
3. Check bot has write permissions
4. Look for uncommitted changes

## Code Quality

- ✅ No syntax errors
- ✅ All imports working
- ✅ Type hints used
- ✅ Comprehensive logging
- ✅ Error handling
- ✅ Unit tests (18 tests)
- ✅ Documentation updated

## Summary

This implementation successfully adds:
1. **24/7 automated vacancy monitoring** with configurable intervals
2. **Robust retry logic** with exponential backoff for API reliability
3. **Admin commands** for code updates and service management
4. **Enhanced help system** showing current bot state
5. **Comprehensive testing** with 18 unit tests (all passing)
6. **Updated documentation** with examples and troubleshooting

The bot is now production-ready for continuous operation with improved reliability, monitoring capabilities, and administrative control.
