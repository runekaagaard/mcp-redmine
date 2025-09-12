# Changelog

All notable changes to this project will be documented in this file.

This fork (`olssonsten/mcp-redmine`) maintains an active, consumable version of the Redmine MCP server when upstream activity is limited.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) with fork suffixes.

## [2025.7.9.post0] - 2025-09-12

### Added
- Fork maintenance infrastructure
- This CHANGELOG.md to track divergences from upstream
- Fork versioning strategy with `.post0` suffix
- Updated project metadata to reflect fork ownership
- Attribution to upstream repository in project URLs

### Changed
- Maintained original `mcp-redmine` package name with new publisher for seamless user experience
- Project URLs to point to fork repository
- Added Sten Olsson as co-author while preserving original author credit
- Updated description to indicate this is an active fork

### Upstream Tracking
- Based on upstream commit: `runekaagaard/mcp-redmine` at version `2025.07.09.120802`
- No functional changes from upstream in this release
- All modifications are metadata and infrastructure only

### Technical Notes
- Updated versioning to use Python-compatible semantic versioning format
- Fork version uses `.post0` suffix to indicate post-release modifications

## Fork Information

**Upstream Repository**: https://github.com/runekaagaard/mcp-redmine  
**Fork Repository**: https://github.com/olssonsten/mcp-redmine  
**License**: Mozilla Public License Version 2.0 (MPL-2.0)  

### Fork Rationale
This fork exists to maintain an active, consumable version of the Redmine MCP server when upstream development is limited. All changes maintain compatibility with the original codebase and preserve the MPL-2.0 license.

### Versioning Strategy
- Base version follows semantic versioning compatible with Python packaging
- Fork releases use `.postN` suffix where N increments for each fork release
- Example: `2025.7.9.post0` (based on upstream `2025.07.09.120802`)