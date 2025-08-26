#!/bin/bash
# Create v2.5 GitHub Issues with Labels and Milestones

# Setup (run once)
echo "🔖 Setting up v2.5 milestone and labels..."

gh label create "v2.5" --color BFD4F2 --description "TaxDoc v2.5" 2>/dev/null || echo "Label v2.5 exists"
gh label create "backend" --color 0366D6 2>/dev/null || echo "Label backend exists"
gh label create "frontend" --color 0E8A16 2>/dev/null || echo "Label frontend exists"
gh label create "stripe" --color F66A0A 2>/dev/null || echo "Label stripe exists"
gh label create "exports" --color 5319E7 2>/dev/null || echo "Label exports exists"
gh label create "imports" --color 1D76DB 2>/dev/null || echo "Label imports exists"
gh label create "observability" --color 0052CC 2>/dev/null || echo "Label observability exists"
gh label create "security" --color D93F0B 2>/dev/null || echo "Label security exists"

gh milestone create "v2.5" --description "Finalize gating, imports/exports, alerts, CORS, dashboards" 2>/dev/null || echo "Milestone v2.5 exists"

echo ""
echo "🚀 Creating v2.5 Issues..."

# EPIC 1 — Billing & Entitlements (Stripe)
gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5: Stripe webhook prod whsec + signature verify" \
  -b "Update webhook URL to https://iljpaj6ogl.execute-api.us-east-1.amazonaws.com/prod/stripe-webhook.

Set env: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, USERS_TABLE, ENVIRONMENT=prod.

Verify with Stripe SDK constructEvent (reject bad signatures; log event.id).

Idempotency: upsert on event.id.

**Acceptance:**
stripe trigger checkout.session.completed → 200 OK.
User plan flips to Starter; log shows \"signature verified\"." \
  -l "v2.5,backend,stripe" -m "v2.5"

gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5: Entitlement middleware + UI gating" \
  -b "DDB Users: { plan, docQuotaMonthly, usedThisMonth, features:{exports:[csv,json,xlsx,pdf], aiInsights, api} }

Middleware checks quota & feature flags; return 402 with upgrade hint.

Frontend hides/greys buttons if not entitled; shows upgrade CTA.

**Acceptance:**
Free hits cap → API 402, UI shows Upgrade. Starter unlocks exports/API." \
  -l "v2.5,backend,stripe" -m "v2.5"

gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5: Monthly quota counter + reset" \
  -b "Increment usedThisMonth on successful extract.

Lambda@Cron (UTC 00:05 1st) resets counters; logs count per tenant.

**Acceptance:**
After cron, counts = 0; previous month totals stored in usageHistory." \
  -l "v2.5,backend,stripe" -m "v2.5"

# EPIC 2 — Imports (fast wins)
gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5: Batch/Folder upload (queue UI + presign)" \
  -b "Implement webkitdirectory multi-upload with queue & progress. Reuse presign → process path.

**AC:** folder of 5 -> all processed; UI responsive." \
  -l "v2.5,frontend,imports" -m "v2.5"

gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5: Mobile camera capture + compression" \
  -b "<input accept=\"image/*\" capture=\"environment\">

Client compress >6MB down to ~2–3MB; autorotate EXIF.

**AC:** Phone photo W-2 uploads <3s on LTE; extract quality OK." \
  -l "v2.5,frontend,imports" -m "v2.5"

gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5: ZIP bulk ingest" \
  -b "Accept .zip to S3; Lambda unzips (PDF/JPG/PNG only) → enqueue each file.

Return files[] + jobId.

**AC:** ZIP with 5 docs → 5 jobs created & processed." \
  -l "v2.5,backend,imports" -m "v2.5"

gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5: Email-to-Upload (MVP)" \
  -b "SES inbound → S3 incoming/{tenant}/{user}/... → SQS → pipeline.

Allowlist sender domain; ignore unsupported attachments.

**AC:** Send 1 PDF → appears in Documents; \"doc-ready\" alert fires." \
  -l "v2.5,backend,imports" -m "v2.5"

# EPIC 3 — Exports
gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5: Export All (ZIP)" \
  -b "Package CSV/JSON/XLSX/PDF into one ZIP; store in exports/...; presigned link 15m.

**AC:** \"Export All\" for 5 docs → ZIP downloads <10s; contents correct." \
  -l "v2.5,backend,exports" -m "v2.5"

gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5: PDF Summary export (1-page)" \
  -b "Generate 1-page summary (key fields, confidence, timestamp, logo). Save to exports; return presigned URL.

**AC:** Opens cleanly; fields match edited values." \
  -l "v2.5,backend,exports" -m "v2.5"

gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5: Email export (link)" \
  -b "SES email with presigned link (no PII in body); link TTL 15m.

**AC:** Email arrives in <60s; link valid; access logged." \
  -l "v2.5,backend,exports" -m "v2.5"

# EPIC 4 — Alerts & Status (SNS)
gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5: doc-ready / doc-failed topics + publish" \
  -b "Create topics; publish on state change with {tenantId, docId, summaryUrl?}.

Subscribe ops email for now.

**AC:** Success & fail flows both email within 60s; no PII in message." \
  -l "v2.5,backend,observability" -m "v2.5"

# EPIC 5 — CORS & Auth (prod hardening)
gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5: API Gateway CORS: exact origin + OPTIONS" \
  -b "Allow origin: http://taxdoc-web-app-v2-prod.s3-website-us-east-1.amazonaws.com

Headers: Authorization,Content-Type; Methods: GET,POST,PUT,DELETE,OPTIONS.

**AC:** Browser: no red CORS errors across Upload/Chat/Exports." \
  -l "v2.5,backend,security" -m "v2.5"

gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5: Auth sanity" \
  -b "/me without token → 401/403; with valid IdToken → 200 with profile.

All protected routes enforce Cognito.

**AC:** Curl tests pass (401/403 vs 200 with JWT)." \
  -l "v2.5,backend,security" -m "v2.5"

# EPIC 6 — Observability
gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5: CloudWatch dashboard + alarms (Upload/Extract/Chat/Exports/Stripe)" \
  -b "Add tiles (invocations, errors, p95) and alarms (>1% errors 5m, webhook 5xx spike, DLQ>0).

**AC:** Dashboard visible; alarm fires on forced failure." \
  -l "v2.5,backend,observability" -m "v2.5"

gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5: Structured logs" \
  -b "JSON logs: traceId, tenantId, userId, docId, step, latencyMs, outcome.

Correlate request → job → export with traceId.

**AC:** Single traceId traces a doc E2E in logs/X-Ray." \
  -l "v2.5,backend,observability" -m "v2.5"

# EPIC 8 — UI Enhancements (v2.5)
gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5 UI: Upload queue + progress + errors" \
  -b "Queue list with filename, size, type icon, progress bar, cancel/retry.

Inline validation (type/size), duplicate detection, auto-rotate image previews.

Graceful errors with toasts.

**AC:** Upload 5 mixed files → all show progress; 1 failure shows retry; duplicates flagged; images auto-rotate." \
  -l "v2.5,frontend,imports" -m "v2.5"

gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5 UI: Import stepper & empty states" \
  -b "Top stepper: Import → Processing → Extracted → Export (sticky).

Empty state cards for each tab with sample doc CTA.

Microcopy under tiles: \"PDF/JPG/PNG • Max 20MB • We auto-rotate & mask SSNs\".

**AC:** Stepper advances automatically; empty states render with sample actions." \
  -l "v2.5,frontend" -m "v2.5"

gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5 UI: Docs grid filters/sort/search + bulk actions" \
  -b "Filters: Type, Confidence (≥), Date, Text search (filename/field).

Sort by Processed date, Confidence, Name.

Checkbox multi-select row; bulk actions: Export All, Delete, Email Link.

**AC:** Filter ≥95% shows only high-confidence docs; multi-select 3 docs → \"Export All (ZIP)\" appears." \
  -l "v2.5,frontend,exports" -m "v2.5"

gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5 UI: Document viewer polish: labels, confidence chips, mask/reveal, copy" \
  -b "Field label-value layout; confidence chip (e.g., 95%) with tooltip.

Mask sensitive (SSN/EIN) by default with \"Reveal\" + audit ping.

Copy buttons per field + \"Copy all as CSV/JSON\" quick actions.

**AC:** Reveal toggles update audit; copying field puts clean value on clipboard; chips show on hover." \
  -l "v2.5,frontend" -m "v2.5"

gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5 UI: Export drawer (one-click)" \
  -b "Right-side drawer with: CSV, JSON, XLSX, PDF Summary, Export All (ZIP), Email Link.

Shows estimated size & link expiry (15m).

**AC:** Drawer opens from \"Export\" button; actions return toast + download or email confirmation." \
  -l "v2.5,frontend,exports" -m "v2.5"

gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5 UI: Live \"Doc Ready\" toast + bell" \
  -b "Poll /status or SSE; show toast when job completes with \"View\" + \"Export\" buttons.

Header bell shows unread completions.

**AC:** Upload → toast appears on completion within polling window; bell count increments." \
  -l "v2.5,frontend" -m "v2.5"

gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5 UI: Usage meter + upgrade CTA" \
  -b "Header pill: \"16/20 this month • Free\" with progress bar + Upgrade button.

Disables gated actions at cap, shows inline CTA.

**AC:** Cap reached → export buttons disabled with tooltip; Upgrade flow accessible." \
  -l "v2.5,frontend,stripe" -m "v2.5"

gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5 UI: Subscriptions page polish" \
  -b "Plan cards: tick/close lists, \"Current plan\" state, tooltip explaining AI insights, API.

Loading state while checking entitlements; error banner on webhook failure.

**AC:** After upgrade, card flips to Current plan without reload (post-refresh token)." \
  -l "v2.5,frontend,stripe" -m "v2.5"

gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5 UI: AI Chat UX: context chips + \"My Document\"" \
  -b "Quick chips: Supported docs, Filing deadlines, Deductions, My Document.

When doc context loaded, show document pill (filename, type, confidence).

Error & thinking indicators; multi-line input with Shift+Enter.

**AC:** Clicking My Document injects doc context; answers reference fields." \
  -l "v2.5,frontend" -m "v2.5"

gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5 UI: Analytics: trend cards + empty/skeleton states" \
  -b "KPI cards with mini-sparklines; last 7 days chart toggle bar/line.

Skeleton loading for dashboards; empty state with \"Process your first doc\".

**AC:** Loading shows skeletons; KPIs render with real values; empty state visible with 0 docs." \
  -l "v2.5,frontend" -m "v2.5"

gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5 UI: Accessibility & responsive sweep" \
  -b "Keyboard: tab order, focus rings, ESC to close dialogs, Enter to submit.

ARIA labels for icons/buttons; contrast ≥ 4.5:1; form error text.

Responsive breakpoints: 360/768/1024, sticky nav safe-area on iOS.

**AC:** Basic keyboard journey completes; Lighthouse a11y ≥ 90." \
  -l "v2.5,frontend" -m "v2.5"

gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5 UI: Global toaster + inline validation utilities" \
  -b "Central toast system (success/info/error) with queue; toast.success(\"Export ready\").

Inline validators for file type/size/email; standard error component.

**AC:** All flows (upload/export/upgrade) use unified toasts; validation consistent." \
  -l "v2.5,frontend" -m "v2.5"

# EPIC 9 — Unknown Docs, Citations, & Trainable Patterns
gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5 UI: Unknown doc — Top Fields + Help me label" \
  -b "Show Top Fields for docType=unknown; drawer to assign labels; save edits to backend; exports use edited labels.

If docType=unknown, show Top Fields section + \"Help me label\" button.

**AC:** unknown doc shows Top Fields; edits persist; audit created." \
  -l "v2.5,frontend" -m "v2.5"

gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5 UI: Field citations — click to highlight region" \
  -b "Return bbox/page with fields; canvas overlay + zoom on click; Esc to clear.

Show citations: click a field → highlight region on preview.

**AC:** highlights correct area for PDF & images." \
  -l "v2.5,frontend" -m "v2.5"

gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5 Backend: Train this pattern (tenant-scoped template)" \
  -b "Create FirmPatterns table; endpoints to create/list/apply; match by header keywords/layoutHash; gate by plan.

\"Train this pattern\" (save custom mappings) for firms—later upsell.

**AC:** labeled doc -> pattern -> similar doc auto-labeled; tenant isolation." \
  -l "v2.5,backend" -m "v2.5"

# EPIC 7 — Go/No-Go (release)
gh issue create -R Cloudwith-mo/taxdoc-microservice \
  -t "v2.5: Test script (copy/paste)" \
  -b "One markdown with curl/stripe/cli steps:

- Stripe webhook 200 & plan flip
- Upload photo + folder + ZIP  
- Export All + PDF Summary + Email export
- SNS alerts
- CORS/Auth checks

**AC:** Script run = all green; sign off." \
  -l "v2.5,backend" -m "v2.5"

echo ""
echo "✅ Created all v2.5 issues!"
echo ""
echo "🎯 Next Steps:"
echo "1. Review issues in GitHub"
echo "2. Assign team members"
echo "3. Start with highest priority items"
echo "4. Track progress in v2.5 milestone"