# `core.plugins` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/plugins/__init__.py`
_Plugin-arkitektur (spec §5). Connector- + kanal-plugins, lokalt forankret._

_(no top-level classes or functions)_

## `core/plugins/base_plugin.py`
_Plugin-kontrakt + registry (spec §5, Fase 5 Task 5.1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `PluginManifest` | `` | Beskriver et plugin uden at indeholde hemmeligheder. | [src](../../../core/plugins/base_plugin.py#L29) |
| method | `PluginManifest.as_dict` | `(self)` | — | [src](../../../core/plugins/base_plugin.py#L40) |
| class | `BasePlugin` | `` | Basis-kontrakt et plugin implementerer. | [src](../../../core/plugins/base_plugin.py#L49) |
| method | `BasePlugin.is_connected` | `(self)` | True hvis plugin'et har en aktiv (klient-rapporteret) forbindelse. | [src](../../../core/plugins/base_plugin.py#L59) |
| method | `BasePlugin.requires_owner` | `(self, action)` | Om en action kræver owner-autoritet (default: nej). Override pr. plugin. | [src](../../../core/plugins/base_plugin.py#L63) |
| function | `register_plugin` | `(manifest)` | Registrér et plugin-manifest. Validerer kind/modes (fail-closed). | [src](../../../core/plugins/base_plugin.py#L73) |
| function | `available_plugins` | `()` | Alle registrerede plugin-manifester. | [src](../../../core/plugins/base_plugin.py#L83) |
| function | `get_manifest` | `(plugin_id)` | — | [src](../../../core/plugins/base_plugin.py#L88) |
| function | `clear_registry` | `()` | Test-helper. | [src](../../../core/plugins/base_plugin.py#L92) |
| function | `set_status` | `(plugin_id, status, *, detail=…)` | Sæt klient-rapporteret status for et plugin (connected|failed|offline). | [src](../../../core/plugins/base_plugin.py#L98) |
| function | `get_status` | `(plugin_id)` | — | [src](../../../core/plugins/base_plugin.py#L110) |

