# Security policy

## Supported versions

Security fixes are currently applied to the latest commit on `main`. The
`v0.1.0` tag is the first frozen API/ABI reference, but no long-term support
window has been promised yet.

## Reporting a vulnerability

Do not publish exploit details, sensitive inputs, or credentials in a public
issue.

Use GitHub's private vulnerability reporting or a private security advisory for
this repository if that option is available. If it is not available, open a
minimal public issue asking the maintainer for a private contact channel; include
no technical details beyond the affected component and your preferred contact
method.

Please include, when safe:

- the affected commit, tag, platform, and interface (Rust, C ABI, or Python);
- reproduction steps or a minimal reproducer;
- expected and observed impact;
- whether the issue involves memory safety, FFI misuse, denial of service,
  malformed audio, or build/release integrity; and
- any proposed embargo or disclosure timeline.

You should receive an acknowledgement after a maintainer sees the report. This
volunteer project does not promise a fixed response or remediation SLA. The
maintainer will coordinate validation, a fix, and disclosure timing with the
reporter where practical.

## Scope note

Incorrect loudness caused by uncalibrated input or an unvalidated measurement
chain is an important product-safety concern, but it is not by itself a software
security vulnerability. Never use this project as the sole basis for hearing
safety or regulatory compliance decisions.
