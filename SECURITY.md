# Security Policy / 安全策略

We take the security of OpenAgent seriously. This document explains which
versions receive security updates and how to report a vulnerability.

我们非常重视 OpenAgent 的安全性。本文档说明哪些版本会获得安全更新,以及如何报告安全漏洞。

## Supported Versions / 支持的版本

OpenAgent is released as source on GitHub. We do not maintain a long-term
semver support matrix. The table below reflects what we actively backport
security fixes to.

OpenAgent 以源码形式在 GitHub 发布,我们并不维护长期 semver 支持矩阵。下表说明我们会为哪些目标主动回移植安全修复。

| Version / 版本 | Supported / 是否支持 |
| -------------- | ------------------- |
| Latest release (`v1.1.4`) | ✅ Supported / 支持 |
| `main` branch / `main` 分支 | ✅ Supported / 支持 |
| Previous minor releases / 之前的次要版本 | ⚠️ Best effort on request / 按需尽力支持 |
| Older releases / 更早的版本 | ❌ Not supported / 不支持,请升级 |

> Always run the latest release or the `main` branch to receive security fixes.
> 请始终使用最新发布版本或 `main` 分支以获得安全修复。

## Reporting a Vulnerability / 报告漏洞

**Please do NOT open a public GitHub issue for security vulnerabilities.**

**请不要为安全漏洞提交公开的 GitHub Issue。**

Report vulnerabilities privately by emailing:
**2227625024@qq.com**

请通过以下邮箱私下报告漏洞:**2227625024@qq.com**

To help us reproduce and fix the issue quickly, please include:

为帮助我们快速复现并修复问题,请在邮件中包含:

- Affected version or commit SHA / 受影响的版本或提交 SHA
- Step-by-step reproduction / 详细的复现步骤
- Impact assessment / 影响评估
- Suggested fix (if any) / 建议的修复方案(如有)

You should receive an initial acknowledgment within **48 hours**. We will
keep you updated on progress and notify you when a fix is released. Please
do not disclose the vulnerability publicly until a patched release is
available.

我们将在 **48 小时内** 给予初步确认,并持续同步修复进度,在补丁版本发布后通知您。在补丁版本发布前,请勿公开披露漏洞。

## Scope / 适用范围

Security issues include but are not limited to: SSRF, authentication or
authorization bypass, secret leakage, SQL injection, remote code execution,
and any flaw that compromises the confidentiality, integrity, or
availability of an OpenAgent deployment.

安全问题包括但不限于:SSRF、身份认证或鉴权绕过、密钥泄露、SQL 注入、远程代码执行,以及任何危害 OpenAgent 部署机密性、完整性或可用性的缺陷。

## Acknowledgments / 致谢

With your permission, we credit responsible reporters in the project README,
following the same practice used for previous security reports.

在征得您同意后,我们会在项目 README 中致谢负责任的报告者,与此前安全报告的处理方式一致。
