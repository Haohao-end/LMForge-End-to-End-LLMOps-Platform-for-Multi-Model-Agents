# Security Policy

We take the security of OpenAgent seriously. This document explains which
versions receive security updates and how to report a vulnerability.

## Supported Versions

OpenAgent is released as source on GitHub. We do not maintain a long-term
semver support matrix. The table below reflects what we actively backport
security fixes to.

| Version | Supported |
| ------- | ---------- |
| Latest release (`v1.1.4`) | ✅ Supported |
| `main` branch | ✅ Supported |
| Previous minor releases | ⚠️ Best effort on request |
| Older releases | ❌ Not supported — please upgrade |

> Always run the latest release or the `main` branch to receive security fixes.

## Reporting a Vulnerability

**Please do NOT open a public GitHub issue for security vulnerabilities.**

Report vulnerabilities privately by emailing:
**2227625024@qq.com**

To help us reproduce and fix the issue quickly, please include:

- Affected version or commit SHA
- Step-by-step reproduction
- Impact assessment
- Suggested fix (if any)

You should receive an initial acknowledgment within **48 hours**. We will
keep you updated on progress and notify you when a fix is released. Please
do not disclose the vulnerability publicly until a patched release is
available.

## Scope

Security issues include but are not limited to: SSRF, authentication or
authorization bypass, secret leakage, SQL injection, remote code execution,
and any flaw that compromises the confidentiality, integrity, or
availability of an OpenAgent deployment.

## Acknowledgments

With your permission, we credit responsible reporters in the project README,
following the same practice used for previous security reports.
