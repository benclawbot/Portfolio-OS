# Runtime configuration

Portfolio OS loads JSON configuration from `portfolio-os.json` by default or from the path in `PORTFOLIO_OS_CONFIG`.

```json
{
  "workspace": "/home/user/.portfolio-os",
  "github": {
    "owner": "benclawbot",
    "api_url": "https://api.github.com"
  },
  "analysis": {
    "disabled_analyzers": [],
    "max_file_bytes": 2000000,
    "fail_on_plugin_error": false
  },
  "logging": {
    "level": "INFO",
    "json": false
  },
  "profiles": {
    "ci": {
      "workspace": "/tmp/portfolio-os-ci",
      "analysis": {
        "fail_on_plugin_error": true
      },
      "logging": {
        "json": true
      }
    }
  }
}
```

Select a profile with:

```bash
export PORTFOLIO_OS_PROFILE=ci
portfolio-refresh --pretty
```

Profile objects are recursively merged over the top-level defaults. Unknown profiles and invalid non-object configuration roots fail clearly.

GitHub credentials are never stored in configuration. Supply `GITHUB_TOKEN` or `GH_TOKEN` through the environment or a secret manager.
