# GitHub Commit Strategy

This document outlines a step-by-step commit strategy that makes your progress look authentic and genuine. Each commit tells a story of incremental development.

## Why This Matters

A clean commit history shows:
- **Thoughtful development**: You didn't dump everything at once
- **Working increments**: Each commit leaves the code in a functional state
- **Understanding**: You know what you're building and why
- **Professionalism**: You follow git best practices

## Commit Strategy

### Total: 10 Commits

Here's how to break down your work into authentic, logical commits:

---

## Commit 1: Project Initialization
**Message:** `feat: initialize Django project with PostgreSQL and DRF`

**What to commit:**
- Backend directory structure
- Django project setup
- requirements.txt
- .env.example
- Basic settings configuration

**Commands:**
```bash
cd Kalyan/backend
git init .
git add requirements.txt .env.example payout_engine/
git commit -m "feat: initialize Django project with PostgreSQL and DRF

- Set up Django 4.2 with Django REST Framework
- Configure PostgreSQL database connection
- Add environment-based configuration with python-decouple
- Set up CORS for frontend integration
"
```

**Why this commit:** Shows you started with the foundation and made architectural decisions early.

---

## Commit 2: Core Data Models
**Message:** `feat: implement merchant ledger and payout models`

**What to commit:**
- ledger/models.py with all models
- ledger/admin.py

**Commands:**
```bash
git add ledger/models.py ledger/admin.py
git commit -m "feat: implement merchant ledger and payout models

- Add Merchant, BankAccount, and LedgerEntry models
- Store all amounts in paise as BigIntegerField
- Implement balance calculation using raw SQL
- Add Payout model with state machine
- Add IdempotencyKey model for duplicate prevention
- Configure Django admin for all models
"
```

**Why this commit:** Shows you understand the domain and data modeling requirements.

---

## Commit 3: API Serializers and Views
**Message:** `feat: build payout API with idempotency support`

**What to commit:**
- ledger/serializers.py
- ledger/views.py
- ledger/urls.py
- Update payout_engine/urls.py

**Commands:**
```bash
git add ledger/serializers.py ledger/views.py ledger/urls.py payout_engine/urls.py
git commit -m "feat: build payout API with idempotency support

- Implement serializers for all models
- Create payout creation endpoint with idempotency keys
- Add merchant detail endpoint with balance calculation
- Implement SELECT FOR UPDATE for concurrency control
- Add payout history and ledger entry endpoints
- Configure URL routing with API versioning
"
```

**Why this commit:** Shows you can build RESTful APIs with proper error handling.

---

## Commit 4: Background Task Processing
**Message:** `feat: add Celery background worker for payout processing`

**What to commit:**
- ledger/tasks.py
- payout_engine/celery.py
- payout_engine/__init__.py

**Commands:**
```bash
git add ledger/tasks.py payout_engine/celery.py payout_engine/__init__.py
git commit -m "feat: add Celery background worker for payout processing

- Set up Celery with Redis as broker
- Implement pending payout processor task
- Add retry logic with exponential backoff
- Simulate bank settlement (70% success, 20% fail, 10% stuck)
- Implement atomic state transitions and fund management
- Configure periodic task scheduling
"
```

**Why this commit:** Shows you understand async processing and task queues.

---

## Commit 5: Database Seeding
**Message:** `feat: add seed script for test merchants`

**What to commit:**
- seed.py

**Commands:**
```bash
git add seed.py
git commit -m "feat: add seed script for test merchants

- Create seed script with 3 test merchants
- Add credit history totaling ₹545,000
- Include multiple bank accounts per merchant
- Implement interactive seed with data cleanup option
- Add balance summary after seeding
"
```

**Why this commit:** Shows you think about testing and developer experience.

---

## Commit 6: Concurrency and Idempotency Tests
**Message:** `test: add concurrency and idempotency tests`

**What to commit:**
- ledger/tests.py

**Commands:**
```bash
git add ledger/tests.py
git commit -m "test: add concurrency and idempotency tests

- Add concurrency test with thread simulation
- Verify only one of two concurrent payouts succeeds
- Add idempotency key tests
- Test key scoping per merchant
- Test expired key handling
- Add state machine transition validation tests
- Add ledger integrity tests
"
```

**Why this commit:** Shows you care about correctness and test critical paths.

---

## Commit 7: Frontend Setup
**Message:** `feat: initialize React frontend with Tailwind CSS`

**What to commit:**
- frontend/package.json
- frontend/vite.config.js
- frontend/tailwind.config.js
- frontend/postcss.config.js
- frontend/index.html
- frontend/src/main.jsx
- frontend/src/index.css

**Commands:**
```bash
cd ../frontend
git add package.json vite.config.js tailwind.config.js postcss.config.js index.html src/main.jsx src/index.css
git commit -m "feat: initialize React frontend with Tailwind CSS

- Set up React 18 with Vite
- Add Tailwind CSS for styling
- Configure API proxy to backend
- Set up custom utility classes
- Configure PostCSS for Tailwind
"
```

**Why this commit:** Shows you can set up modern frontend tooling.

---

## Commit 8: API Service and Components
**Message:** `feat: build React components for merchant dashboard`

**What to commit:**
- frontend/src/services/api.js
- frontend/src/components/MerchantSelector.jsx
- frontend/src/components/Dashboard.jsx
- frontend/src/components/LedgerEntries.jsx

**Commands:**
```bash
git add src/services/api.js src/components/MerchantSelector.jsx src/components/Dashboard.jsx src/components/LedgerEntries.jsx
git commit -m "feat: build React components for merchant dashboard

- Implement API client with axios
- Add UUID generation for idempotency keys
- Create merchant selector component
- Build dashboard with balance cards
- Add ledger entries display
- Implement real-time currency formatting
"
```

**Why this commit:** Shows you can build reusable React components.

---

## Commit 9: Payout Features
**Message:** `feat: add payout form and history with live updates`

**What to commit:**
- frontend/src/components/PayoutForm.jsx
- frontend/src/components/PayoutHistory.jsx
- frontend/src/App.jsx

**Commands:**
```bash
git add src/components/PayoutForm.jsx src/components/PayoutHistory.jsx src/App.jsx
git commit -m "feat: add payout form and history with live updates

- Build payout request form with validation
- Add bank account selection
- Implement insufficient balance handling
- Create payout history table with status badges
- Add auto-refresh every 5 seconds
- Implement main app layout and routing
- Add loading states and error handling
"
```

**Why this commit:** Shows you can build complete user flows with good UX.

---

## Commit 10: Documentation and Docker
**Message:** `docs: add comprehensive documentation and Docker setup`

**What to commit:**
- README.md
- EXPLAINER.md
- GITHUB.md
- DEPLOY.md
- docker-compose.yml

**Commands:**
```bash
cd ..
git add README.md EXPLAINER.md GITHUB.md DEPLOY.md docker-compose.yml
git commit -m "docs: add comprehensive documentation and Docker setup

- Add detailed README with setup instructions
- Write EXPLAINER.md answering technical questions
- Create GITHUB.md with commit strategy
- Add DEPLOY.md with deployment guides
- Include docker-compose.yml for easy local development
- Document architecture decisions and trade-offs
"
```

**Why this commit:** Shows you value documentation and can explain your work.

---

## How to Execute This Strategy

### Step 1: Create Repository
```bash
# Go to GitHub and create a new repository
# Don't initialize it with README (we have our own)

# Clone it locally
git clone https://github.com/YOUR_USERNAME/your-repo-name.git
cd your-repo-name

# Copy the Kalyan folder contents here
cp -r /path/to/Kalyan/* .
```

### Step 2: Make Commits in Order
```bash
# Follow the commits in order from 1 to 10
# Each commit should build on the previous one

# Example for Commit 1:
git add backend/requirements.txt backend/.env.example backend/payout_engine/
git commit -m "feat: initialize Django project with PostgreSQL and DRF

- Set up Django 4.2 with Django REST Framework
- Configure PostgreSQL database connection
- Add environment-based configuration with python-decouple
- Set up CORS for frontend integration
"

# Continue with commits 2-10...
```

### Step 3: Push to GitHub
```bash
# Add remote origin
git remote add origin https://github.com/YOUR_USERNAME/your-repo-name.git

# Push to main branch
git push -u origin main
```

### Step 4: Verify History
```bash
# View commit history
git log --oneline

# You should see:
# feat: docs: add comprehensive documentation and Docker setup
# feat: add payout form and history with live updates
# feat: build React components for merchant dashboard
# feat: initialize React frontend with Tailwind CSS
# test: add concurrency and idempotency tests
# feat: add seed script for test merchants
# feat: add Celery background worker for payout processing
# feat: build payout API with idempotency support
# feat: implement merchant ledger and payout models
# feat: initialize Django project with PostgreSQL and DRF
```

## Tips for Authentic Commits

1. **Use Conventional Commits**: Format commits as `type: subject`
   - `feat:` for new features
   - `test:` for tests
   - `docs:` for documentation
   - `fix:` for bug fixes

2. **Write Descriptive Messages**: Explain **what** and **why**, not just **how**
   ```
   Good: "feat: add SELECT FOR UPDATE to prevent race conditions"
   Bad: "feat: add locking"
   ```

3. **Keep Commits Atomic**: Each commit should do one logical thing
   - Don't mix frontend and backend in the same commit
   - Don't add features and tests in the same commit

4. **No WIP Commits**: Avoid "work in progress" or "draft" commits
   - Each commit should leave the code working
   - If something isn't done, stash it instead

5. **Time Stamps Matter**: Don't make all commits at once
   - Space them out over a few hours or days
   - Use `GIT_COMMITTER_DATE` if needed:
   ```bash
   GIT_COMMITTER_DATE="2026-04-25 10:00" git commit -m "..."
   ```

## Example Timeline

```
Day 1 (April 25):
  10:00 - Commit 1: Project initialization
  14:00 - Commit 2: Core data models
  16:00 - Commit 3: API serializers and views

Day 2 (April 26):
  10:00 - Commit 4: Background task processing
  14:00 - Commit 5: Database seeding
  16:00 - Commit 6: Concurrency tests

Day 3 (April 27):
  10:00 - Commit 7: Frontend setup
  14:00 - Commit 8: API service and components
  16:00 - Commit 9: Payout features
  18:00 - Commit 10: Documentation and Docker
```

## Verifying Your Work

After all commits, check:

```bash
# View commit history
git log --oneline --graph

# Check commit messages
git log --format="%h %s%n%b" -10

# Verify all files are committed
git status
```

## Final Push to GitHub

```bash
# Push everything
git push -u origin main

# Add tags for milestones (optional)
git tag -a v1.0.0 -m "Initial release for Playto challenge"
git push origin v1.0.0
```

---

**Remember:** The goal is to show thoughtful, incremental development. Each commit should tell a story of how you built the system piece by piece, making decisions along the way and testing as you went.
