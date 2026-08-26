# Third-Party Notices

ChronosFix core runtime code uses only the Python standard library. The following
third-party tools and hosted actions participate in packaging, continuous
integration, or deployment. They are not copied into the ChronosFix source tree.

## Python build tooling

| Component | Configured version | Purpose | License | Source |
|---|---|---|---|---|
| setuptools | `>=68` (build-time only) | PEP 517 build backend and editable install | MIT | <https://github.com/pypa/setuptools> |
| PyYAML | `>=6.0.2,<7` (optional validation extra) | Parse and statically validate AgentTeams declarations; it does not deploy a runtime | MIT | <https://github.com/yaml/pyyaml> |

## GitHub Actions used by this repository

The workflow references below are the actual major-version tags configured in
`.github/workflows/`. GitHub resolves those tags when a workflow run starts.

| Action | Configured ref | Workflow purpose | License | Source |
|---|---|---|---|---|
| actions/checkout | `v4` | Check out the repository for verification and Pages deployment | MIT | <https://github.com/actions/checkout> |
| actions/setup-python | `v5` | Provision Python 3.10, 3.11, and 3.12 for the engineering gate | MIT | <https://github.com/actions/setup-python> |
| actions/configure-pages | `v5` | Configure GitHub Pages metadata | MIT | <https://github.com/actions/configure-pages> |
| actions/upload-pages-artifact | `v3` | Package the static Repair Cockpit site for Pages | MIT | <https://github.com/actions/upload-pages-artifact> |
| actions/deploy-pages | `v4` | Publish the packaged static artifact to GitHub Pages | MIT | <https://github.com/actions/deploy-pages> |

| jsonschema | `>=4.21,<5` (optional validation extra) | Validate the public Draft 2020-12 scenario contract | MIT | <https://github.com/python-jsonschema/jsonschema> |
| actions/upload-artifact | `v4` | Preserve semifinal acceptance JSON/Markdown as workflow evidence | MIT | <https://github.com/actions/upload-artifact> |

## Declared external integration targets

AgentTeams and Alibaba Cloud Skills are external integration targets described by
resource declarations and adapters in this repository. They are not vendored by
ChronosFix, and the repository does not claim that every optional cloud component
has been provisioned. Upstream identities used for reproducible validation are
recorded separately in `agentteams/runtime/dependency-lock.json`.

## Software inventory

`SBOM.json` is a review-time CycloneDX inventory for the distributable Python
package and the workflow dependencies above. It is an inventory and attribution
aid, not a claim that external services are deployed.
