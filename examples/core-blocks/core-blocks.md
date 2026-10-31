---
title: Core Blocks
section: "1"
tab: CORE
handbook: Sheet Reference
system: "CORE BLOCKS -- parts, status, linked diagrams, traces and a glossary"
doc: CORE-1
mission: the reference
date: 10.31.2026
by: "A worked example of the five blocks that organize a long document. Renders to paper with sheet.py and to the screen with web.py."
---

## Functional description

A long document reads best in parts. Each part opens with a thesis and lists its sections, every section carries
a status, the system map links each box to the part that explains it, a trace walks one request through the
whole system, and the glossary defines each term once. The first use of a term, such as a lease or the ledger,
gets a card on the screen.

:::diagram System Map
grid 1.6 0.9
node req "REQUEST" 0 0 round link=#part-intake
node queue "QUEUE" 1 0 drum link=#the-queue
node work "WORKER" 2 0 link=#part-work
node led "LEDGER" 2 1 drum link=#the-ledger
edge req queue
edge queue work "LEASE"
edge work led "APPEND"
:::

# Intake {#part-intake}

:::part
thesis: A request is accepted once, written down before anything acts on it, and never lost after that.
:::

## The front door {#front-door status=built}

Requests arrive over one socket. The door checks the shape, assigns an id and hands the request to
[the queue](#the-queue). It answers the caller at once; the work happens later.

| Field | Meaning |
|---|---|
| id | assigned at the door, never reused |
| body | the request as sent |

## The queue {status=prototyped}

A worker takes a request by writing a lease with an expiry; a lease that runs out returns the request to the
queue. See [the trace](#fig-I.2.1) for the whole path.

:::trace One Request, Door to Ledger
step "accept" | the door checks the shape and assigns an id | #front-door
step "enqueue" | the request is written to the queue before the caller hears back | #the-queue
step "lease" | a worker writes a lease with a five minute expiry | #the-queue
step "work" | the worker runs the request; a crash lets the lease expire | #the-worker
step "append" | the result is appended to the ledger, and the lease is released | #the-ledger
:::

# Work {#part-work}

:::part
thesis: Workers judge; the ledger keeps the record. Nothing that moves work forward lives only in a worker's head.
:::

## The worker {status=designed}

### Retries {status=speculative}

A failed request goes back once with a note; a second failure goes to a person.

## The ledger {#the-ledger status=built}

Every result is one appended line, in order. Status is derived from the ledger, never kept by hand.

:::note
A section without a status is fine where it describes no mechanism, like this example's glossary.
:::

## Glossary

:::glossary
lease | a claim on one request with an expiry; when it runs out, the request returns to the queue
ledger | the append-only record of every result, in order
thesis | the one or two sentences that open a part and say what it argues
:::
