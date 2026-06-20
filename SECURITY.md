# Security Policy

## Supported Versions

This project is currently pre-1.0. Security fixes are applied to the latest `main` branch and to any public release series explicitly listed in release notes.

## Reporting a Vulnerability

Please do not open a public issue for a suspected vulnerability.

Until a dedicated security contact is published, report security concerns privately to the repository owner. Include:

- a description of the issue and affected functionality;
- steps to reproduce or a minimal proof of concept;
- the expected impact;
- any suggested mitigation, if known.

The maintainer will acknowledge valid reports as soon as practical, investigate the issue, and coordinate disclosure once a fix is available.

## Scope

In scope:

- code execution, packaging, or dependency issues introduced by this repository;
- malformed puzzle input that causes unexpected file access, shell execution, or denial of service beyond normal solver cost;
- CI or release automation issues that could compromise published artifacts.

Out of scope:

- intentionally hard Sudoku puzzles that take longer to solve;
- correctness limitations already documented for human-style solving techniques;
- vulnerabilities in third-party services or data sources not controlled by this project.
