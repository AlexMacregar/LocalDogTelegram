# Security Policy

[English](SECURITY_EN.md) | [Русский](SECURITY_RU.md)

## Reporting a Vulnerability

We take the security of LocalDog seriously. If you find a security vulnerability, please do not open a public issue. Instead, please report it privately.

You can report vulnerabilities by:
1. Opening a private draft security advisory on GitHub (if available).
2. Contacting the maintainer directly via Telegram: [@Alex_Macregar](https://t.me/Alex_Macregar)

We will acknowledge your report within 48 hours and provide a timeline for a fix.

## Supported Versions

Currently, only the latest version of LocalDog is supported for security updates.

## Local-only nature
LocalDog is designed to be a local proxy. By default, it listens on `127.0.0.1`. Changing this to `0.0.0.0` will make the proxy accessible to anyone on your network. Use this with caution and ensure you use a strong, secret key.
