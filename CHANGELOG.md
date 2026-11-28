# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- One-command engine installer for the invoking user on Linux and macOS: it
  installs the engine, places its entry point in a command directory, makes that
  directory reachable in newly started terminal sessions and verifies the
  result before reporting the installed version.
- Pre-install version determination: the installer reports the version a
  configured source and release reference would install, without installing or
  changing anything, so a caller can compare it against an installed engine.
- A documented comparison rule for keeping an engine current: only a strictly
  newer available version replaces an installed engine; an equal or older
  available version leaves it untouched.
- Removal that takes back the engine, its entry point and the installer's
  start-up contribution, and keeps the user's configuration and project
  material.
- A directly consumable engine version report: the engine answers which version
  it is with one JSON object on standard output, without a project, a model
  credential or a particular working directory, as the supported compatibility
  judgement for another tool.
