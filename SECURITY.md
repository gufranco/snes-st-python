# Security

## Reporting

Report anything you believe is a security problem through
[GitHub's private vulnerability reporting](https://docs.github.com/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability)
on this repository, rather than in a public issue. There is no service behind
this and no user data, so the realistic reports are about the supply chain and
about what a malformed input can make the code do.

## What is in scope

| Class | Example |
|-------|---------|
| Supply chain | A dependency or a pinned action that has been compromised |
| Malformed input | A crafted image that makes the loader allocate without bound, or microcode that never halts |
| Path handling | An input that causes a write outside the directory the caller named |
| Image handling | Anything that lets a file the manifest did not name be loaded and run |

## What is not

A conformance disagreement is a correctness bug and belongs in a normal issue.
So does a model that disagrees with real hardware. Neither is a security matter,
and filing them privately only slows the fix.

## What this repository reads, and what it never keeps

This package runs microcode. That microcode belongs to whoever made the part, is
not carried here in any form, and is supplied by whoever holds a copy. What is
carried is a manifest: the length and four digests of each image, with SHA-256
deciding. A file that does not match is refused rather than run.

A report that the image path can be made to load a file the manifest did not
name, or to read past the end of one, is in scope and is the most interesting
thing here. Running the wrong image would report behaviour no hardware has,
which is worse than reporting nothing.

Nothing reaches the network. Any file this package reads is one already on the
machine because somebody put it there.
