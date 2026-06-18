# Sources of Customer Problems — A 5-Tier Signal Framework

## Overview

The best startup ideas come from real, unsolved customer problems. But not all problem signals are created equal. This framework ranks **where** you find problems by signal quality — from raw, unsolicited complaints to echo-chamber discussions everyone has already seen.

The core insight: **negative reviews are startup ideas in disguise. Manual work is an automation opportunity. If companies hire for a task repeatedly, software can replace it.**

## The 5 Tiers

### Tier 1 — Public Unsolicited Complaints (Multiplier: 1.0×)

**Sources:** Reddit, Hacker News, Indie Hackers, X/Twitter, WorldMonitor briefs

**Why valuable:** These are raw, unfiltered pain points expressed in public without prompting. People are not evaluating alternatives — they are simply venting, asking for help, or expressing frustration. This is the purest signal: someone is experiencing a problem badly enough to write about it publicly.

**How to mine:**
- Reddit: Monitor 10–15 seed subreddits (r/smallbusiness, r/Entrepreneur, r/freelance, r/SaaS, r/webdev, r/sysadmin, r/legal, r/RealEstate, r/Accounting, r/healthIT, r/logistics, r/Construction, r/restaurant, r/ecommerce, r/marketing). Beyond seeds, periodically search target industry subreddits with problem-indicator keywords.
- Hacker News: The `/ask` and `/show` sections. "Ask HN: What's your biggest pain point?" threads are gold.
- Indie Hackers: "What are you struggling with?" threads, product hunt alternatives discussions.
- X/Twitter: Follow developers, marketers, agencies, e-commerce operators, and AI users. Search for "any tool for", "wish there was", "why is there no".
- WorldMonitor: Geopolitical and economic briefs that surface regulatory shifts, supply chain disruptions, and emerging market gaps.

**Example keywords:** "hate", "frustrated", "nightmare", "killing me", "can't stand", "any tool for", "wish there was", "why is there no", "someone should build".

---

### Tier 2 — Professional Communities & Review Sites (Multiplier: 1.3×)

**Sources:** Slack/Discord communities, Facebook Groups, support forums, G2, Capterra, Trustpilot

**Why valuable:** People here are **evaluating alternatives** and writing detailed complaints. A negative review on G2 or Capterra is someone who already bought a solution, found it lacking, and took the time to explain why. That is market-proven demand. Professional communities (Slack channels, Discord servers, FB groups) contain practitioners discussing real workflow gaps with peers — more detailed and actionable than public social media.

**How to mine:**
- **G2 (g2.com):** Browse software category pages → sort by lowest-rated → extract 1–2 star reviews. Category examples: payroll, CRM, project management, accounting.
- **Capterra (capterra.com):** Same approach — category pages → sort by rating ascending → extract review text.
- **Trustpilot (trustpilot.com):** Target company-specific review pages in industries matching your expertise.
- **Professional communities:** Search for "looking for", "alternative to", "switched from X to Y because", "anyone else using".

**Example keywords:** "switched from", "alternative to", "looking for", "disappointed with", "worst part is", "if only it could", "missing feature".

**Scrape strategy:** Maintain 20–30 software categories relevant to target industries. Fetch first 3 pages of lowest-rated reviews every 30 min. Extract review title + body, pass through LLM: "This review of [product] describes a pain point. Extract the underlying problem."

**Bonus signal:** When a reviewer writes "I switched from X to Y because...", that is a direct statement about what X failed to do. Extract both the problem AND the competitive dynamic.

---

### Tier 3 — Job Boards & Consulting Marketplaces (Multiplier: 1.2×)

**Sources:** Upwork, Fiverr, LinkedIn job listings, consulting marketplaces

**Why valuable:** **Market proof — money is already being spent.** If companies repeatedly hire people to perform a repetitive task, that task is a software opportunity. The fact that someone is paying for it validates demand without any guesswork. If hundreds of freelancers sell the same service, software may automate or productize it.

**How to mine:**
- **Upwork:** Search job categories matching target industries. Filter for recurring roles: data entry, reporting, compliance, content operations, customer support. Keywords: "manual data entry", "generate reports", "compliance check", "content operations".
- **Fiverr:** Browse gig categories. If a gig type has hundreds of sellers (e.g., "Shopify product listing optimization", "resume formatting", "podcast editing"), there's scale worth automating.
- **LinkedIn:** Search for job titles that repeat across companies for the same manual function. Look for "specialist" or "analyst" roles that are essentially manual data pipelines.

**LLM prompt:** "This job listing describes a task people are paid to do. Could this task be partially or fully automated by software? If yes, describe the automation opportunity as a problem statement."

**Example keywords:** "data entry", "report generation", "compliance", "manual", "spreadsheet", "reconciliation", "migration", "audit".

**Scrape strategy:** Every 60 min (low frequency — job listings don't change rapidly). Use `httpx` with 2s polite delays between requests.

---

### Tier 4 — Developer & User Pain Documented in Detail (Multiplier: 1.1×)

**Sources:** GitHub Issues, browser extension reviews, YouTube comments, app store reviews

**Why valuable:** GitHub Issues are **gold mines most people ignore.** Developer pain is documented with technical context, reproduction steps, and feature gap analysis. Issues labeled `feature` or `enhancement` with high reaction counts represent widespread unsolved problems with a technical audience. App store reviews (especially 1–2 star) contain direct statements of unmet needs from non-technical users.

**How to mine:**
- **GitHub Issues:** Search API (`/search/issues`). Sort by reactions (+1 count), filter to open issues with > 50 reactions, within last 6 months. Query: `is:issue is:open sort:reactions-+1 created:>2026-01-01`. Focus on `feature`, `enhancement`, `bug` labels with high reaction counts.
- **Browser extension reviews:** Chrome Web Store, Firefox Add-ons — look for "wish it could", "would be perfect if".
- **YouTube comments:** On tutorial/software review videos — "this is great but what I really need is...".
- **App store reviews:** 1–2 star reviews on competing products. "This app doesn't do X" = feature gap.

**LLM prompt:** "This GitHub issue describes a feature gap or pain point. Extract the underlying problem that this feature would solve."

**Example keywords:** "feature request", "would be nice if", "blocking", "workaround", "hacky", "janky", "missing", "broken workflow".

**Rate limit note:** GitHub Search API is 30 req/min authenticated (personal access token, no special scopes), 10 req/min unauthenticated. ~10 queries per cycle is safe.

---

### Tier 5 — Founder Communities & Build-in-Public Groups (Multiplier: 0.8×)

**Sources:** Product Hunt, founder communities, build-in-public groups, startup Twitter

**Why valuable (with caution):** These communities surface what **builders think** is important — which may or may not align with what customers actually need. Useful for feedback on existing ideas and competitive landscape awareness, but weaker for novel market discovery. **Echo chamber risk:** everyone sees the same discussions.

**How to mine:**
- Product Hunt: New launches and discussions. Look for products getting traction that solve problems you hadn't considered.
- Founder communities: Indie Hackers, MicroConf, YC forums. Look for build-in-public threads where founders share what they're learning.
- Build-in-public Twitter: Founders sharing revenue, churn, customer feedback.

**When to use:** Cross-reference ideas found here against Tier 1–3 sources. If a problem only appears in founder communities, it may be a solution in search of a problem.

**Example keywords:** "launching", "building in public", "monthly revenue", "customer discovery", "what I learned from".

---

## Highest ROI Workflow

The most efficient signal pipeline combines tiers for validation:

1. **Seed discovery (Tier 1):** Monitor Reddit, HN, Twitter for problem signals. This is your firehose — broad, unfiltered, real-time.
2. **Cross-reference with review sites (Tier 2):** When a problem surfaces on Reddit, check if it also appears in G2/Capterra/Trustpilot reviews for products in that space. If people are complaining about the same thing in structured reviews, the signal is real.
3. **Validate via job boards (Tier 3):** Check Upwork/Fiverr — are people being paid to solve this problem manually? If yes, the market is proven.
4. **Deepen via GitHub (Tier 4):** If the problem has a technical component, search GitHub Issues for related feature requests.
5. **Optional: Founder check (Tier 5):** See if anyone is already building this. If 10 people are, you're late. If 0–2 are, the opportunity may be real.

**A problem discovered on Reddit (Tier 1) that also appears in G2 reviews (Tier 2) and has freelancers being paid to solve it on Upwork (Tier 3) gets scored at the highest tier among its mentions (Tier 2, 1.3×).**

---

## Keyword Glossary for Scraping

### Explicit Frustration
`hate`, `frustrated`, `nightmare`, `killing me`, `can't stand`, `ruining`, `infuriating`, `drives me crazy`, `worst experience`, `garbage`, `useless`, `broken`, `terrible`, `awful`, `horrible`

### Workaround Signal (strongest indicator of software opportunity)
`manual`, `spreadsheet`, `workaround`, `duct tape`, `hacky`, `janky`, `manual process`, `copy paste`, `export to excel`, `do it by hand`, `emailing back and forth`, `tracking in sheets`, `still using`

### Active Search
`any tool for`, `does anyone else`, `why is there no`, `someone should build`, `wish there was`, `how do you handle`, `what do you use for`, `looking for a tool`, `recommend a`, `alternative to`, `better way to`

### Desperation
`desperate`, `please someone`, `I would pay anything`, `life depends on`, `this is costing us`, `losing money`, `bleeding money`, `can't afford to`, `make or break`, `critical`, `urgent`

### Revenue Signal (rare but strongest single signal)
`$X/month`, `paying for`, `spent $X on`, `costs us $X`, `budget for`, `investing in`, `subscription`

### Comparison / Switching
`switched from X to Y`, `migrated from`, `replaced X with`, `X vs Y`, `better than`, `cheaper than`, `X but for`

### Negative Review Patterns
`would be great if`, `only thing missing`, `dealbreaker`, `had to stop using`, `cancelled my subscription`, `asked for refund`, `waste of money`

---

## Summary Principles

1. **Negative reviews are startup ideas in disguise.** Every 1–2 star review on G2, Capterra, or an app store describes a problem someone already paid to solve — and the solution failed them.

2. **Manual work = automation opportunity.** If you see "spreadsheet", "manual", "copy-paste", or "do it by hand" in a professional context, there is software waiting to be built.

3. **If companies hire for it repeatedly, software can replace it.** Job board listings for repetitive tasks are market-proven demand. The budget is already allocated.

4. **Cross-tier validation beats single-source discovery.** A problem that appears in Reddit comments AND G2 reviews AND Upwork job listings is almost certainly real.

5. **The best signal is unsolicited.** Tier 1 beats Tier 5 because people saying "this sucks" spontaneously is more honest than a founder pitching their solution.
