# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 4.0.x | yes |
| older | no |

## Reporting a vulnerability

Please do not open a public issue for a security problem. Use GitHub's private
vulnerability reporting:

<https://github.com/AndyPischka/LibreCharts/security/advisories/new>

Include the LibreCharts version, the LibreOffice version and operating system, and the
steps that reproduce the problem. We aim to acknowledge a report within seven days and to
publish a fix and an advisory once a fix is available.

## Scope

LibreCharts is a LibreOffice Impress extension written in Python-UNO. It runs inside
LibreOffice with the rights of the user who started LibreOffice.

- The extension itself makes no network requests and sends no telemetry.
- Linked data sources (Calc, Excel, CSV) are opened hidden, read-only and without running
  macros. LibreCharts reads their cell values; it does not modify the files.
- Chart data and settings are stored in the presentation document.
- The extension does not execute code from documents or data files.

Out of scope: vulnerabilities in LibreOffice itself, in a linked file, or in the operating
system. Report those to the respective project.
