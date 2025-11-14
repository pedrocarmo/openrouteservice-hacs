# HACS Version Error Research

**Date**: 2025-11-14
**Issue**: "The version xxxx for this integration can not be used with HACS"

## Problem Summary

User is receiving a HACS error when attempting to add the OpenRouteService integration as a custom repository. The error indicates the version cannot be used with HACS.

## Current Repository State

- **Repository**: `pedrocarmo/openrouteservice-hacs`
- **Git Tag**: `v0.0.1` (exists and pushed to remote)
- **GitHub Release**: `v0.0.1` (Pre-release, created 2025-11-14)
- **manifest.json version**: `0.0.1` (matches tag)
- **Missing**: `hacs.json` file in repository root

## HACS Requirements Research

### Essential Files for HACS Custom Repository

1. **hacs.json** (REQUIRED in repository root)
   - Minimum required field: `name`
   - Optional but important fields:
     - `render_readme`: Display README in HACS UI
     - `homeassistant`: Minimum HA version requirement
     - `zip_release`: For zipped releases
     - `filename`: Name of zip file if using zip_release

2. **manifest.json** (in custom_components/DOMAIN/)
   - Must include: `domain`, `documentation`, `issue_tracker`, `codeowners`, `name`, `version`
   - All fields present in current implementation ✅

3. **GitHub Releases** (optional but recommended)
   - Tags alone are insufficient
   - Full releases enable version selection in HACS UI
   - Current: v0.0.1 release exists ✅

### Repository Structure Requirements

```
repository-root/
├── hacs.json                          ❌ MISSING
├── README.md                          ✅ Present
├── custom_components/
│   └── openrouteservice/
│       ├── __init__.py                ✅ Present
│       ├── manifest.json              ✅ Present
│       ├── config_flow.py             ✅ Present
│       ├── api.py                     ✅ Present
│       └── ...
```

## Root Cause Analysis

Based on research, the error "The version xxxx for this integration can not be used with HACS" can be caused by:

1. **Missing hacs.json file** (Most likely)
   - HACS requires this file to recognize the repository as a valid custom repository
   - Without it, HACS cannot properly validate or install the integration

2. **Version Format Issues**
   - HACS has known issues with non-standard version formats
   - Current version "0.0.1" is standard semantic versioning ✅

3. **Home Assistant Version Compatibility**
   - manifest.json may specify minimum HA version that user doesn't meet
   - Current manifest.json doesn't specify `homeassistant` field
   - May need to specify minimum version in hacs.json

4. **Version Comparison Bug**
   - HACS GitHub issue #4423 documents version parsing bugs
   - Can affect installations from HEAD or non-standard versions
   - Less likely with our semantic versioning approach

## Reference Implementation: hass_omie

The working example (https://github.com/luuuis/hass_omie) has:

```json
{
  "name": "OMIE",
  "render_readme": true,
  "zip_release": true,
  "filename": "hass_omie.zip",
  "homeassistant": "2023.1.0"
}
```

Key observations:
- Uses `zip_release` with `filename` for distribution
- Specifies minimum Home Assistant version
- Enables README rendering
- 26 releases with automated versioning via release-please

## Recommended Solution

Create a `hacs.json` file in the repository root with minimal required configuration:

```json
{
  "name": "OpenRouteService",
  "render_readme": true,
  "homeassistant": "2023.1.0"
}
```

Optional enhancements:
- Add `zip_release` and `filename` if using zipped releases
- Specify minimum `homeassistant` version to prevent compatibility issues
- Consider adding `hacs` minimum version if needed

## Additional Considerations

1. **Brand Registration**: Integration should be registered in home-assistant/brands repository (future enhancement)

2. **Release Strategy**:
   - Current: Using GitHub pre-releases
   - Consider: Full releases for production versions
   - Consider: Automated releases with release-please or similar

3. **Documentation**:
   - README should include HACS installation instructions
   - Document minimum Home Assistant version requirements

## Next Steps

1. Create hacs.json file in repository root
2. Commit and push the change
3. Test adding the custom repository in HACS
4. If still failing, investigate:
   - User's Home Assistant version
   - HACS version
   - Exact error message details

## References

- HACS Integration Docs: https://www.hacs.xyz/docs/publish/integration/
- HACS Start Guide: https://www.hacs.xyz/docs/publish/start/
- HACS Custom Repositories: https://www.hacs.xyz/docs/faq/custom_repositories/
- Reference Implementation: https://github.com/luuuis/hass_omie
- HACS Issue #4423: Version comparison bug
