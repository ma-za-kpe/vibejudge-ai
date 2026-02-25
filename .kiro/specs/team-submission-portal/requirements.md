# Team Submission Portal - Requirements

## Overview

Build a public-facing web interface for hackathon teams to submit their GitHub repositories for VibeJudge AI analysis. The portal provides real-time validation, submission confirmation, and post-analysis feedback display. This completes the platform by connecting teams → organizers → judges.

## Goals

- Enable teams to self-submit repositories without organizer intervention
- Validate GitHub repository accessibility before submission
- Provide instant submission confirmation with tracking ID
- Display analysis results and scorecard after judging completes
- Support QR code submission for mobile/event kiosks
- Ensure lightweight, fast loading (<2 seconds on 3G)
- Work on all devices (mobile, tablet, desktop)

## Non-Goals

- Team account creation/authentication (anonymous submission initially)
- Payment processing (teams don't pay, organizers do)
- Real-time collaboration features (Google Docs-style editing)
- GitHub OAuth integration (public repo URL submission only)
- Complex form builders for custom rubrics

---

## Requirements

### Requirement 1: Hackathon-Specific Submission Page

**User Story:** As a hackathon organizer, I want a unique URL for my event where teams can submit.

**Acceptance Criteria:**
1.1. URL format: vibejudge.ai/submit/{hackathon_slug} (e.g., /submit/ghana-innovation-2025)
1.2. Page displays hackathon name, description, submission deadline
1.3. Page fetches hackathon details via GET /api/v1/hackathons/{hack_id}/public
1.4. Invalid hackathon_slug shows 404 with search functionality
1.5. Expired hackathons (past end_date) show "Submissions Closed" message
1.6. Page loads in <2 seconds on 3G network
1.7. Page is mobile-responsive (works on viewport 320px+)

### Requirement 2: Team Submission Form

**User Story:** As a team member, I want to submit our project with minimal friction.

**Acceptance Criteria:**
2.1. Form fields: team_name (required, 1-100 chars), github_repo_url (required, valid URL), team_members (optional, comma-separated names)
2.2. GitHub URL validation: must be github.com URL, must be accessible (200 status)
2.3. Real-time validation: URL checked on blur, shows ✅ or ❌ before submit
2.4. Duplicate submission detection: same repo can't be submitted twice
2.5. Submit button disabled until all validations pass
2.6. Form submission via POST /api/v1/hackathons/{hack_id}/submissions
2.7. Loading spinner during submission (typical: 2-5 seconds)

### Requirement 3: GitHub Repository Validation

**User Story:** As a platform operator, I want to validate repositories are accessible before expensive analysis.

**Acceptance Criteria:**
3.1. Client-side check: URL matches github.com/{owner}/{repo} pattern
3.2. Server-side check: HEAD request to https://github.com/{owner}/{repo} returns 200
3.3. Private repository detection: Returns 404 → show error "Repository must be public"
3.4. Non-existent repository: Returns 404 → show error "Repository not found"
3.5. Archived repository: Warning shown but submission allowed
3.6. Empty repository (0 commits): Warning shown but submission allowed
3.7. Validation errors show helpful messages with GitHub URL formatting guide

### Requirement 4: Submission Confirmation

**User Story:** As a team member, I want immediate confirmation that our submission was received.

**Acceptance Criteria:**
4.1. Success page shows: submission_id (ULID), team_name, timestamp, hackathon name
4.2. Success page shows: "Submitted successfully! Save this ID: {submission_id}"
4.3. Success page has "Copy Submission ID" button
4.4. Success page shows estimated analysis completion time (e.g., "Results available in ~30 minutes")
4.5. Success page has "View Status" link to /submit/{hackathon_slug}/status/{submission_id}
4.6. Confirmation email sent to optional team email (if provided)
4.7. Submission receipt is printer-friendly (for event kiosks)

### Requirement 5: Submission Status Tracking

**User Story:** As a team member, I want to check if our analysis is complete without contacting organizers.

**Acceptance Criteria:**
5.1. Status page: /submit/{hackathon_slug}/status/{submission_id}
5.2. Page shows submission metadata: team name, repo URL, submitted time
5.3. Page shows analysis status: pending, analyzing, completed, failed
5.4. "Analyzing" status shows progress bar and estimated completion time
5.5. "Completed" status shows overall score and recommendation
5.6. "Failed" status shows error message and retry option
5.7. Page auto-refreshes every 10 seconds while status is "analyzing"

### Requirement 6: Scorecard Display (Post-Analysis)

**User Story:** As a team member, I want to see our detailed scorecard after analysis completes.

**Acceptance Criteria:**
6.1. Scorecard shows: overall_score, confidence, recommendation
6.2. Scorecard shows dimension scores: code_quality, innovation, performance, authenticity
6.3. Scorecard shows agent summaries (collapsed by default, expandable)
6.4. Scorecard shows strengths and improvements from each agent
6.5. Scorecard shows team dynamics and strategy analysis
6.6. Scorecard shows actionable feedback for each team member
6.7. Scorecard does NOT show file:line citations (organizer-only for security)

### Requirement 7: QR Code Submission Flow

**User Story:** As an event organizer, I want to display QR codes at the venue for easy mobile submission.

**Acceptance Criteria:**
7.1. QR code generated for URL: vibejudge.ai/submit/{hackathon_slug}
7.2. QR code downloadable as PNG, SVG, PDF (for printing)
7.3. QR code page optimized for mobile (large touch targets, minimal typing)
7.4. QR code landing page has autofocus on team_name field
7.5. Mobile keyboard defaults to URL keyboard for GitHub URL field
7.6. Success page shows large, scannable submission ID QR code
7.7. QR code submission flow completes in <60 seconds

### Requirement 8: Multi-Language Support (Future-Proofing)

**User Story:** As an international organizer, I want the portal available in multiple languages.

**Acceptance Criteria:**
8.1. Portal detects browser language (Accept-Language header)
8.2. Supported languages: English, French, Spanish (others future)
8.3. Language selector in footer allows manual override
8.4. All UI strings externalized to i18n JSON files
8.5. Form validation messages translated
8.6. Error messages translated
8.7. Success confirmations translated

### Requirement 9: Accessibility (WCAG 2.1 AA)

**User Story:** As an accessibility advocate, I want the portal usable by people with disabilities.

**Acceptance Criteria:**
9.1. All form fields have accessible labels (not placeholder-only)
9.2. Color contrast ratio >4.5:1 for all text
9.3. Keyboard navigation works (tab through form, submit with Enter)
9.4. Screen reader announces validation errors
9.5. Focus indicators visible on all interactive elements
9.6. Error messages associated with fields via aria-describedby
9.7. WAVE accessibility checker shows 0 errors

### Requirement 10: Rate Limiting and Abuse Prevention

**User Story:** As a platform operator, I want to prevent spam submissions without blocking legitimate teams.

**Acceptance Criteria:**
10.1. IP-based rate limit: 5 submissions per hour per IP
10.2. Exceeded rate limit shows: "Too many submissions. Try again in {minutes} minutes"
10.3. CAPTCHA required after 3 submissions from same IP
10.4. Honeypot field (hidden) catches bots
10.5. Duplicate team names from same IP flagged for review
10.6. Form submission requires user interaction (no direct POST to API)
10.7. Rate limit counters stored in DynamoDB with TTL

### Requirement 11: Organizer Embed Widget

**User Story:** As a hackathon organizer, I want to embed the submission form on my event website.

**Acceptance Criteria:**
11.1. Embed code available: `<iframe src="vibejudge.ai/submit/{slug}/embed">`
11.2. Embedded version is minimal (no header/footer)
11.3. Embedded version resizes dynamically based on content
11.4. Embedded version posts message to parent on submission success
11.5. Organizer can customize embed: brand color, logo, custom success message
11.6. Embed works on HTTPS sites only (security)
11.7. Embed snippet generator in organizer dashboard

### Requirement 12: Offline Submission Support

**User Story:** As a team at a hackathon with poor WiFi, I want to submit even with intermittent connectivity.

**Acceptance Criteria:**
12.1. Form data saved to localStorage on every field change
12.2. Form pre-fills from localStorage on page reload
12.3. "Offline" banner shown when network disconnected
12.4. Submission queued when offline, auto-submits when connection restored
12.5. Service worker caches static assets for offline page load
12.6. LocalStorage cleared after successful submission
12.7. Queued submissions stored max 24 hours then deleted

### Requirement 13: Error Handling and Recovery

**User Story:** As a team member, I want clear guidance when submission fails.

**Acceptance Criteria:**
13.1. GitHub validation failure shows: "Repository must be public. Here's how to make it public: [link]"
13.2. Duplicate submission shows: "This repository was already submitted by '{other_team_name}' on {date}"
13.3. Hackathon closed shows: "Submissions ended on {date}. Contact organizer for late submission."
13.4. Network timeout shows: "Connection lost. Click to retry."
13.5. Server error (500) shows: "Something went wrong. Try again or contact support."
13.6. Budget exceeded shows: "Organizer budget limit reached. Contact them to increase."
13.7. All errors have "What to do next" section with actionable steps

### Requirement 14: Analytics and Metrics

**User Story:** As a product manager, I want to track portal usage to optimize conversion.

**Acceptance Criteria:**
14.1. Track: page views, form starts, form completions, submission success rate
14.2. Track: average time to complete form
14.3. Track: validation error rates (which fields fail most often)
14.4. Track: mobile vs desktop submission ratio
14.5. Track: QR code vs direct URL submission ratio
14.6. Analytics sent to CloudWatch or Google Analytics
14.7. Privacy-compliant (no PII tracking, GDPR-friendly)

### Requirement 15: Email Notifications (Optional)

**User Story:** As a team member, I want email updates about our submission status.

**Acceptance Criteria:**
15.1. Submission form has optional email field
15.2. Confirmation email sent immediately with submission ID
15.3. Status update email sent when analysis completes
15.4. Email includes: team name, hackathon name, scorecard link
15.5. Email has unsubscribe link (one-click opt-out)
15.6. Email templates branded with VibeJudge logo
15.7. Email delivery via AWS SES or SendGrid

### Requirement 16: Technology Stack (Implementation Choices)

**User Story:** As a developer, I want to choose the best tech stack for fast development and great UX.

**Acceptance Criteria:**
16.1. Option A: Static HTML + Alpine.js (lightweight, no build step)
16.2. Option B: Streamlit (Python, matches organizer dashboard)
16.3. Option C: Next.js (React, modern, best UX)
16.4. Chosen stack must support: SSR/SSG for fast initial load
16.5. Chosen stack must support: client-side validation before API call
16.6. Chosen stack must support: progressive web app (offline support)
16.7. Bundle size <200KB gzipped for mobile performance

### Requirement 17: Deployment and Hosting

**User Story:** As a DevOps engineer, I want the portal deployed independently from backend API.

**Acceptance Criteria:**
17.1. Portal hosted on: Vercel, Netlify, or AWS Amplify (choose one)
17.2. Custom domain: submit.vibejudge.ai
17.3. HTTPS enforced (HTTP redirects to HTTPS)
17.4. CDN caching for static assets (images, CSS, JS)
17.5. GitHub Actions deploys on push to main branch
17.6. Preview deployments for pull requests
17.7. Zero-downtime deployments (rolling release)

### Requirement 18: Organizer Preview Mode

**User Story:** As an organizer, I want to preview how the submission portal looks before going live.

**Acceptance Criteria:**
18.1. Preview URL: /submit/{hackathon_slug}?preview=true
18.2. Preview mode shows banner: "PREVIEW MODE - Submissions will not be saved"
18.3. Preview mode allows form submission but doesn't save to database
18.4. Preview mode accessible only to authenticated organizers
18.5. Preview mode shows test data (sample team names, repos)
18.6. Preview mode allows organizer to customize: logo, colors, welcome text
18.7. Changes in preview mode can be published to live portal

### Requirement 19: Security and Privacy

**User Story:** As a security engineer, I want to protect user data and prevent malicious submissions.

**Acceptance Criteria:**
19.1. All API calls use HTTPS
19.2. No sensitive data logged (GitHub URLs are public but not logged)
19.3. CSRF protection via SameSite cookies
19.4. Content Security Policy header prevents XSS
19.5. Input sanitization prevents SQL injection (even though using DynamoDB)
19.6. Team names sanitized to prevent HTML/JS injection
19.7. Privacy policy link in footer (GDPR/CCPA compliant)

### Requirement 20: Mobile-First Design

**User Story:** As a team member submitting on my phone at the hackathon, I want a great mobile experience.

**Acceptance Criteria:**
20.1. Form optimized for touch (large buttons, adequate spacing)
20.2. GitHub URL field uses URL keyboard on mobile (shows .com key)
20.3. Team name field uses text keyboard with autocapitalize
20.4. Success page fits on screen without scrolling
20.5. QR code scanner integration (if browser supports)
20.6. Submission ID copyable with one tap
20.7. Mobile Lighthouse score >90 (performance, accessibility, best practices)

---

## Technical Constraints

1. **API Endpoint:** Existing backend at https://2nu0j4n648.execute-api.us-east-1.amazonaws.com/dev
2. **Authentication:** No auth required for submission (public endpoint)
3. **Browser Support:** Last 2 versions of Chrome, Firefox, Safari, Edge
4. **Performance:** Lighthouse score >90 on mobile
5. **Bundle Size:** <200KB gzipped JavaScript
6. **Offline Support:** Service worker for core functionality

## Dependencies

- Backend API endpoint: POST /api/v1/hackathons/{hack_id}/submissions
- Backend API endpoint: GET /api/v1/hackathons/{hack_id}/public (hackathon details)
- Backend API endpoint: GET /api/v1/submissions/{sub_id}/status
- Email service (AWS SES or SendGrid) for notifications
- CDN (CloudFront) for asset delivery

## Success Metrics

- **Conversion Rate:** >80% of teams who start form complete submission
- **Load Time:** <2 seconds on 3G network (Lighthouse)
- **Error Rate:** <5% of submissions fail validation
- **Mobile Usage:** >50% of submissions from mobile devices
- **Accessibility:** WAVE scan shows 0 errors
- **User Satisfaction:** Embedded feedback widget shows >4/5 stars

## Out of Scope (Future Enhancements)

- Team account creation (login to view past submissions)
- Submission editing after initial submit
- File upload (supplementary materials like slide decks)
- Video demo upload integration
- Social sharing (share scorecard on Twitter/LinkedIn)
- Multi-submission support (same team, multiple projects)
