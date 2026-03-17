# Narrative Risk Simulator: Simple Product Overview

## What is this product?

Narrative Risk Simulator is a simple AI tool for sports communications teams.

It helps a team review a draft statement before publishing it. The tool checks the draft against past statements, crisis examples, policy rules, sponsor guidance, and current narrative themes. Then it shows where the draft may create public, sponsor, legal, or media risk.

In simple terms, it acts like an internal pre-publication risk check for PR and communications content.

## Why was it built?

Sports organizations often need to publish messages quickly. These can include sponsor announcements, apologies, executive quotes, press releases, or policy-related statements.

The problem is that a message can look fine internally but still create backlash outside. Fans, media, sponsors, and policy stakeholders may all react differently.

This product was built to:

- help teams catch risky language before it goes live
- reduce avoidable backlash and confusion
- give communication teams a faster first review
- support better wording with evidence, not just instinct

## What features exist in this POC today?

The current proof of concept already includes:

- a simple Streamlit interface for internal use
- a text box where a user can paste a draft statement
- support for uploading `txt`, `md`, `csv`, and `json` source files
- a seeded demo knowledge base, so the app works on first launch
- document parsing and chunking for uploaded and seeded content
- local embedding-based retrieval to find related evidence
- an overall risk score from `0` to `100`
- category scores for fan backlash, sponsor risk, legal/policy risk, and media escalation
- top risk reasons
- likely narrative pathways
- a publish verdict: `Safe to publish`, `Needs review`, or `Hold`
- retrieved evidence snippets to explain the result
- a safer rewritten version of the draft
- a local embedding cache to avoid reprocessing unchanged content

## What can be added next?

Useful next steps for this product could include:

- team- or league-specific knowledge bases
- live news, social media, and trend monitoring
- approval workflows for PR, legal, and sponsor teams
- user accounts and role-based access
- audit logs showing who reviewed and changed a draft
- side-by-side comparisons between original and rewritten drafts
- scenario simulation for different audience groups
- historical reporting to show common risk patterns over time
- integrations with CMS, Slack, email, or internal comms tools
- support for more industries beyond sports

## Why is this less available in the market?

Tools like this are still uncommon because the problem is harder than it looks.

Main reasons:

- most communication risk depends on context, timing, and brand history
- good results need private internal data, which many companies do not want to share with vendors
- many teams still handle message review through people, meetings, and manual approvals
- narrative risk is harder to measure than spelling, grammar, or sentiment
- companies worry about trust, false positives, and legal sensitivity
- building a useful product needs both AI capability and domain knowledge in communications

So while there are tools for social listening, media monitoring, sentiment analysis, and brand safety, there are fewer tools focused on pre-publication narrative risk simulation for draft statements.

## Short summary

Narrative Risk Simulator is an early-stage internal AI product that helps sports communications teams test drafts before publishing. The POC already shows strong value by combining retrieval, risk scoring, evidence, and safer rewrites. With live data, workflow features, and organization-specific knowledge, it could become a stronger decision-support product.
