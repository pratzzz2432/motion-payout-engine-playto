# Pre-Submission Checklist

Before submitting to Playto, go through this checklist to ensure everything is complete.

## ✅ Backend Requirements

### Core Features
- [x] Merchant ledger with balance in paise (BigIntegerField)
- [x] No FloatField or DecimalField for money
- [x] Balance calculation using database-level SQL
- [x] Payout request API: POST /api/v1/merchants/{id}/payouts/
- [x] Idempotency-Key header support
- [x] Held funds for pending payouts
- [x] Background worker (Celery) for payout processing
- [x] State machine: PENDING → PROCESSING → COMPLETED/FAILED
- [x] Retry logic with exponential backoff
- [x] Maximum 3 retry attempts
- [x] Fund return on failed payouts

### Technical Constraints
- [x] Concurrency control using SELECT FOR UPDATE
- [x] Idempotency keys scoped per merchant
- [x] Idempotency keys expire after 24 hours
- [x] State transitions validated
- [x] Terminal states (COMPLETED, FAILED) can't transition
- [x] Atomic operations with transaction.atomic()

### Code Quality
- [x] Clean, readable code with comments
- [x] Proper error handling
- [x] Input validation
- [x] SQL injection protection (parameterized queries)
- [x] No hardcoded secrets

## ✅ Frontend Requirements

### Features
- [x] Merchant dashboard with balance display
- [x] Available balance
- [x] Held balance
- [x] Total balance
- [x] Recent ledger entries (credits/debits)
- [x] Payout request form
- [x] Bank account selection
- [x] Amount validation (insufficient balance check)
- [x] Payout history table
- [x] Live status updates (auto-refresh every 5s)
- [x] Status badges with icons
- [x] Responsive design (mobile-friendly)

### User Experience
- [x] Clear error messages
- [x] Loading states
- [x] Form validation
- [x] Success notifications
- [x] Auto-refresh for real-time updates

## ✅ Testing

### Required Tests
- [x] Concurrency test: Two simultaneous payouts, only one succeeds
- [x] Idempotency test: Same key returns cached response
- [x] State machine test: Invalid transitions blocked
- [x] Ledger integrity test: credits - debits = balance

### Test Coverage
- [x] Tests pass locally
- [x] Tests use threading for real concurrency
- [x] Tests verify invariants hold true

## ✅ Documentation

### Required Documents
- [x] README.md with setup instructions
- [x] EXPLAINER.md answering all 5 questions:
  - [x] The Ledger (balance calculation query + why)
  - [x] The Lock (concurrency code + database primitive)
  - [x] The Idempotency (how it knows + in-flight handling)
  - [x] The State Machine (where failed→completed blocked)
  - [x] The AI Audit (wrong code example + fix)
- [x] Seed script for test data
- [x] Deployment guide (DEPLOY.md)

### Additional Documentation
- [x] GITHUB.md with commit strategy
- [x] PROJECT_SUMMARY.md with overview
- [x] Inline code comments
- [x] API documentation (in this README)

## ✅ Deployment

### Deployment Options
- [x] Railway guide (recommended)
- [x] Render guide
- [x] Fly.io guide
- [x] Vercel guide (frontend only)

### Deployment Checklist
- [ ] Environment variables configured
- [ ] Database migrations run
- [ ] Seed script executed
- [ ] Superuser created
- [ ] Celery worker running
- [ ] Frontend API URL configured
- [ ] HTTPS enabled
- [ ] DNS configured (if custom domain)

## ✅ Git & GitHub

### Repository Setup
- [ ] Repository created on GitHub
- [ ] All code pushed
- [ ] Clean commit history (follow GITHUB.md)
- [ ] Commit messages follow conventions
- [ ] .gitignore configured
- [ ] No sensitive data in repo

### Suggested Commits (10 total)
1. feat: initialize Django project with PostgreSQL and DRF
2. feat: implement merchant ledger and payout models
3. feat: build payout API with idempotency support
4. feat: add Celery background worker for payout processing
5. feat: add seed script for test merchants
6. test: add concurrency and idempotency tests
7. feat: initialize React frontend with Tailwind CSS
8. feat: build React components for merchant dashboard
9. feat: add payout form and history with live updates
10. docs: add comprehensive documentation and Docker setup

## ✅ Functionality Checklist

### Manual Testing Steps
- [ ] Frontend loads at http://localhost:3000
- [ ] Can select a merchant from dropdown
- [ ] Can see available, held, and total balance
- [ ] Can see recent ledger entries
- [ ] Can create a payout request
- [ ] Payout appears in history table
- [ ] Payout status changes (PENDING → PROCESSING → COMPLETED/FAILED)
- [ ] Held balance updates when payout created
- [ ] Available balance updates when payout completes
- [ ] Funds return when payout fails
- [ ] Idempotency works (same key = same response)
- [ ] Admin panel accessible at /admin/
- [ ] Can view merchants, payouts, ledger entries in admin

### API Testing
```bash
# Test API endpoints
curl http://localhost:8000/api/v1/merchants/
curl http://localhost:8000/api/v1/merchants/{id}/
curl http://localhost:8000/api/v1/merchants/{id}/payouts/
curl -X POST http://localhost:8000/api/v1/merchants/{id}/payouts/ \
  -H "Idempotency-Key: $(uuidgen)" \
  -H "Content-Type: application/json" \
  -d '{"amount_paise": 5000, "bank_account_id": "..."}'
```

## ✅ Pre-Interview Preparation

### Be Ready to Explain
1. **The Ledger**:
   - Why single table instead of credits/debits tables?
   - Why database-level aggregation instead of ORM?
   - How does the held balance work?

2. **The Lock**:
   - What is SELECT FOR UPDATE?
   - How does it prevent race conditions?
   - Why not use optimistic locking?

3. **Idempotency**:
   - How do you handle in-flight requests?
   - Why PostgreSQL instead of Redis?
   - How do expired keys work?

4. **State Machine**:
   - Where is validation enforced?
   - Why are terminal states important?
   - What happens on illegal transition?

5. **AI Audit**:
   - What wrong code did AI give you?
   - Why was it wrong?
   - How did you fix it?

### System Design Questions
- How would you scale to 1M merchants?
- How would you add webhook notifications?
- How would you handle multi-currency?
- How would you add audit logging?
- How would you implement rate limiting?

### Trade-offs Discussion
- Why paise instead of Decimal?
- Why PostgreSQL instead of MongoDB?
- Why Celery instead of asyncio?
- Why pessimistic locking instead of optimistic?
- Why held funds instead of reserved balance?

## ✅ Final Checks

### Code Quality
- [ ] No TODO comments in production code
- [ ] No console.log statements in frontend
- [ ] No print statements in backend (use logging)
- [ ] No commented-out code
- [ ] No unused imports
- [ ] Proper error messages (not "Error occurred")

### Security
- [ ] SECRET_KEY is strong (not default)
- [ ] DEBUG = False in production
- [ ] ALLOWED_HOSTS configured correctly
- [ ] No sensitive data in git
- [ ] SQL injection protection
- [ ] XSS protection (React escapes by default)

### Performance
- [ ] Database queries are optimized
- [ ] No N+1 queries
- [ ] Pagination implemented (or dataset is small)
- [ ] No unnecessary data fetched
- [ ] Celery workers have appropriate concurrency

## ✅ Submission Form

Before submitting, have ready:
- [ ] GitHub repository URL (public)
- [ ] Deployed frontend URL
- [ ] Deployed backend URL (optional, but good to include)
- [ ] Short note on what you're most proud of (3-4 sentences)

### Example Pride Note:
```
"I'm most proud of the concurrency control implementation. Using PostgreSQL's
SELECT FOR UPDATE with pessimistic locking ensures that even under high load,
no money can be lost or created through race conditions. The ledger model
with database-level balance calculation creates a perfect audit trail and
prevents inconsistencies. This is how real payment systems like Stripe handle
concurrency, and I'm proud I got it working correctly."
```

## After Submission

### Monitor Your Deployment
- Check logs daily
- Verify payouts are processing
- Test the live demo yourself
- Be ready to explain any issues

### Prepare for Technical Screen
- Re-read EXPLAINER.md
- Review your code
- Test the system manually
- Prepare questions for them

### If Shortlisted
- You'll have 45 min with CTO
- Be ready to do live coding
- They may ask you to modify the system
- Be honest about what you don't know

### Final Interview
- 30 min with CEO
- More cultural fit than technical
- Show enthusiasm
- Ask good questions

---

## Timeline Reminder

- **Submission**: 5 days from email receipt
- **CTO Review**: 1-2 days after submission
- **Technical Screen**: 45 minutes if shortlisted
- **CEO Chat**: 30 minutes if technical screen goes well
- **Offer**: Within 48 hours of CEO chat

**Good luck! You've built something to be proud of. 🚀**
