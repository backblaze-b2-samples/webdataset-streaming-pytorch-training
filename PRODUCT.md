# Product

## Register

product

## Users

ML engineers and platform teams evaluating **object storage as the data plane for
training**. Their context: the training corpus already lives on Backblaze B2, and they
want a proven pattern for streaming it into PyTorch without staging it on local disk —
sharding with WebDataset, a manifest index, a custom `s3://` opener, and the worker/node
split that scales reads across GPUs/nodes from one bucket. AI coding agents also read
the repo to extend it for a real corpus.

## Product Purpose

A working reference app (Next.js 16 + React 19 + Tailwind v4 + shadcn/ui frontend,
FastAPI backend) that packs media into WebDataset `.tar` shards, writes them and a JSON
manifest directly to Backblaze B2, then streams them back through WebDataset/WebLoader
into a bounded PyTorch loop that reports live throughput. Everything runs on local
open-source (PyTorch + WebDataset, device auto-detected CUDA → MPS → CPU); B2 credentials
are the only secret. Success = a user can create a dataset, watch shards land on B2, and
stream them into a training loop in seconds — and trust the pattern enough to point it at
their own corpus.

## Maturity and Support Boundary

This is a maintained open-source sample, not a complete hosted training service or a
large-scale distributed trainer (the PyTorch loop is a deliberately tiny, bounded CNN
that demonstrates streaming throughput, not model quality). It is built with
production-minded controls and can be adapted with caution, but adopters own
product-specific validation, security, deployment, and operations. Repository defects go
through the public GitHub issue tracker; B2 account, billing, service, and API questions
go through Backblaze Support. The sample is not covered by the Backblaze service level
agreement, and no SLA is provided for the repository software.

## Brand Personality

Confident, precise, quietly professional. Voice is direct and free of hype ("Stream
your corpus straight from B2 into PyTorch"). The interface should feel like a modern
developer/ML tool — considered, calm, trustworthy — not a marketing showpiece. The
design carries craft through restraint, not through a loud opinionated identity.

## Anti-references

- **Generic AI/SaaS slop.** No gradient text, hero-metric templates, identical
  icon-card grids, tracked uppercase eyebrows, or decorative glassmorphism. These are
  the exact 2026 AI tells this kit exists to help builders avoid.
- **Over-branded / loud.** No heavy brand-color drenching, decorative motion, or flashy
  effects. It is scaffolding to be rebranded, not a hero page.
- **Toy / prototype feel.** No missing states, inconsistent components, or placeholder
  polish. Must read as polished, dependable scaffolding.
- **Enterprise-drab.** No Bootstrap-era gray boxes or dense-but-lifeless admin-panel
  look. Considered, like modern dev tools (Linear, GitHub Primer, Stripe).

## Design Principles

- **Practice what you preach.** The kit itself must model the engineering quality it
  asks agents to produce. Slop here propagates into every project built on it.
- **Neutral foundation, easy to rebrand.** Identity lives in tokens (`globals.css`) and
  one config file. Screens are built from the shared UI kit so a rebrand is a token
  swap, not a rewrite.
- **Earned familiarity over novelty.** Use standard, trusted affordances (top bar +
  side nav, command palette, data tables). The tool disappears into the task.
- **Every state is designed.** Default, hover, focus, active, disabled, loading (skeleton),
  empty (teaches the interface), and error (says what's wrong + offers retry) — never
  half-shipped.
- **Consistency is the feature.** One button vocabulary, one form-control set, one icon
  style across every screen. Divergence is a bug.

## Accessibility & Inclusion

Target **WCAG 2.1 AA**. Body text ≥ 4.5:1, large/bold text ≥ 3:1, visible focus
indicators on every interactive element, full keyboard navigation, correct semantic
landmarks and heading order, labelled form controls, and a `prefers-reduced-motion`
alternative for every animation. Full light and dark theme parity.
