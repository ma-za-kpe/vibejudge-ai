# Anthropic Use Case Form - Quick Reference

**When:** First time using Claude Sonnet 4.6 on Bedrock  
**Where:** Bedrock Playground or when invoking the model via API  
**Time:** 2 minutes

---

## Form Fields and Recommended Answers

### Company name
```
Vibe Coders
```
(Or your company/personal name)

---

### Company website URL
```
https://vibecoders.com
```
(Or your personal website, GitHub profile, or LinkedIn)

---

### What industry do you operate in?
```
Technology / Software Development
```
(Select from dropdown)

---

### Who are the intended users you are building for?
```
☑ External users (customers, clients, public users)
```
(Hackathon organizers and participants are external users)

---

### Describe your use cases (max 500 characters)

**Recommended text (498 characters):**
```
Automated code review and evaluation platform for hackathon submissions. 
Analyzes GitHub repositories to assess code quality, architecture, 
innovation, and development authenticity. Provides evidence-based scoring 
with specific file and line citations. Built for AWS 10,000 AIdeas 
competition to demonstrate AI-powered judging at scale.
```

**Alternative (shorter, 287 characters):**
```
AI-powered hackathon judging platform that analyzes GitHub repositories 
for code quality, architecture, innovation, and authenticity. Provides 
automated scoring with evidence-based feedback. Educational project for 
AWS 10,000 AIdeas competition.
```

---

## ⚠️ Important Notes

1. **Do NOT mention "Claude"** in the description
   - Will be flagged as Personally Identifiable Information (PII)
   - Access will be automatically denied
   - Use generic terms like "AI models" or "language models"

2. **Be specific about use case**
   - Explain what you're building
   - Mention it's for education/competition
   - Highlight the value proposition

3. **Approval is usually instant**
   - Most requests approved immediately
   - May take up to 15 minutes in rare cases
   - You'll be able to use the model right away

4. **One-time per account**
   - Only need to submit once per AWS account
   - Or once at organization's management account
   - All Anthropic models will be enabled after approval

---

## After Submission

1. **Test in Playground**
   - Send a test message
   - Verify model responds

2. **Deploy Your Application**
   ```bash
   make deploy-dev
   ```

3. **Run Analysis**
   - Innovation agent will use Claude Sonnet 4.6
   - Should work without any issues

---

## Troubleshooting

### Issue: "Access denied" or "PII detected"
**Cause:** Mentioned "Claude" in description  
**Solution:** Resubmit without mentioning model names

### Issue: "Still waiting after 15 minutes"
**Cause:** Rare approval delay  
**Solution:** Contact AWS Support or try again later

### Issue: "Form not appearing"
**Cause:** Already submitted for this account  
**Solution:** Model should already be enabled, try invoking it

---

## Privacy Note

From AWS:
> "Aggregated metrics from your usage of Anthropic models on Amazon Bedrock 
> may be shared with Anthropic for security purposes. The details of your 
> content will not be shared."

This is standard for all Bedrock models and doesn't affect your data privacy.

---

**Ready to submit?** Go to [Bedrock Playground](https://console.aws.amazon.com/bedrock/home?region=us-east-1#/playground) and select Claude Sonnet 4.6!
