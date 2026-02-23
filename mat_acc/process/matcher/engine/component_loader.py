# Path: mat_acc/process/matcher/engine/component_loader.py
"""
Component Loader

Loads component definitions from YAML files.
Delegates parsing to component_parser module.
"""

import logging
from pathlib import Path
from typing import Optional

import yaml

from ..models.component_definition import (
    ComponentDefinition,
)
from .component_parser import parse_component


class ComponentLoader:
    """Loads component definitions from YAML files."""

    MARKET_OVERLAYS = {'sec', 'esef'}

    def __init__(
        self, dictionary_path: Optional[Path] = None,
    ):
        """Initialize component loader."""
        self.logger = logging.getLogger(
            'matcher.component_loader',
        )
        if dictionary_path is None:
            self.dictionary_path = (
                Path(__file__).parent.parent.parent.parent
                / 'dictionary'
            )
        else:
            self.dictionary_path = Path(dictionary_path)

        self.components_path = (
            self.dictionary_path / 'components'
        )
        self.formulas_path = (
            self.dictionary_path / 'formulas'
        )
        self._components_cache: Optional[
            dict[str, ComponentDefinition]
        ] = None
        self._market_cache: dict[
            str, dict[str, ComponentDefinition]
        ] = {}

    def _is_overlay_path(self, file_path: Path) -> bool:
        """Check if a YAML file is inside a market overlay dir."""
        rel = file_path.relative_to(self.components_path)
        top_dir = rel.parts[0] if rel.parts else ''
        return top_dir.lower() in self.MARKET_OVERLAYS

    def load_all(
        self, use_cache: bool = True,
    ) -> dict[str, ComponentDefinition]:
        """Load base component definitions (no overlays)."""
        if use_cache and self._components_cache is not None:
            return self._components_cache

        components = {}
        if not self.components_path.exists():
            self.logger.warning(
                f"Components dir not found: "
                f"{self.components_path}"
            )
            return components

        yaml_files = [
            f for f in self.components_path.rglob('*.yaml')
            if not self._is_overlay_path(f)
        ]
        yaml_files.extend(
            f for f in self.components_path.rglob('*.yml')
            if not self._is_overlay_path(f)
        )
        self.logger.info(
            f"Found {len(yaml_files)} component files",
        )

        for yaml_file in yaml_files:
            try:
                component = self.load_file(yaml_file)
                if component:
                    if component.component_id in components:
                        self.logger.warning(
                            f"Duplicate: "
                            f"{component.component_id}"
                        )
                    components[
                        component.component_id
                    ] = component
            except Exception as e:
                self.logger.error(
                    f"Failed to load {yaml_file}: {e}"
                )

        self.logger.info(
            f"Loaded {len(components)} components",
        )
        self._components_cache = components
        return components

    def load_for_market(
        self, market: str,
    ) -> dict[str, ComponentDefinition]:
        """Load components with market-specific overlays."""
        market_lower = market.lower()
        if market_lower in self._market_cache:
            return self._market_cache[market_lower]

        base = self.load_all()
        overlay_dir = self.components_path / market_lower
        if not overlay_dir.exists():
            self.logger.info(
                f"No overlay for '{market_lower}'",
            )
            self._market_cache[market_lower] = base
            return base

        overlays = self._load_overlays(overlay_dir)
        if not overlays:
            self._market_cache[market_lower] = base
            return base

        merged = self._apply_overlays(
            base, overlays, overlay_dir,
        )
        self.logger.info(
            f"Applied {len(overlays)} "
            f"{market_lower} overlays"
        )
        self._market_cache[market_lower] = merged
        return merged

    def _load_overlays(
        self, overlay_dir: Path,
    ) -> dict[str, dict]:
        """Load overlay raw YAML keyed by component_id."""
        overlay_files = list(
            overlay_dir.rglob('*.yaml'),
        )
        overlay_files.extend(
            overlay_dir.rglob('*.yml'),
        )
        overlays = {}
        for f in overlay_files:
            try:
                with open(f, 'r', encoding='utf-8') as fh:
                    data = yaml.safe_load(fh)
                if data and 'component_id' in data:
                    overlays[data['component_id']] = data
            except Exception as e:
                self.logger.error(
                    f"Error loading overlay {f}: {e}"
                )
        return overlays

    def _apply_overlays(
        self, base, overlays, overlay_dir,
    ) -> dict[str, ComponentDefinition]:
        """Apply overlay dicts onto base components."""
        merged = {}
        for cid, comp in base.items():
            if cid not in overlays:
                merged[cid] = comp
                continue
            base_yaml = self._load_raw_yaml_for(cid)
            if base_yaml is None:
                merged[cid] = comp
                continue
            merged_yaml = self._deep_merge(
                base_yaml, overlays[cid],
            )
            try:
                source = overlay_dir / f"{cid}.yaml"
                merged[cid] = parse_component(
                    merged_yaml, source,
                )
            except Exception as e:
                self.logger.error(
                    f"Failed overlay merge {cid}: {e}"
                )
                merged[cid] = comp
        return merged

    def _load_raw_yaml_for(
        self, component_id: str,
    ) -> Optional[dict]:
        """Load raw YAML dict for a base component."""
        for f in self.components_path.rglob('*.yaml'):
            if self._is_overlay_path(f):
                continue
            try:
                with open(f, 'r', encoding='utf-8') as fh:
                    data = yaml.safe_load(fh)
                if data and data.get('component_id') == component_id:
                    return data
            except Exception:
                continue
        return None

    _APPEND_LIST_KEYS = {'reject_if'}

    def _deep_merge(
        self, base: dict, overlay: dict,
    ) -> dict:
        """Deep-merge overlay onto base dict."""
        result = dict(base)
        for key, val in overlay.items():
            if key == 'component_id':
                continue
            if (
                isinstance(val, dict)
                and key in result
                and isinstance(result[key], dict)
            ):
                result[key] = self._deep_merge(
                    result[key], val,
                )
            elif (
                key in self._APPEND_LIST_KEYS
                and isinstance(val, list)
                and key in result
                and isinstance(result[key], list)
            ):
                result[key] = result[key] + val
            else:
                result[key] = val
        return result

    def load_file(
        self, file_path: Path,
    ) -> Optional[ComponentDefinition]:
        """Load a single component from a YAML file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            if data is None:
                self.logger.warning(
                    f"Empty file: {file_path}",
                )
                return None
            return parse_component(data, file_path)
        except yaml.YAMLError as e:
            self.logger.error(
                f"YAML parse error in {file_path}: {e}"
            )
            return None
        except Exception as e:
            self.logger.error(
                f"Error loading {file_path}: {e}"
            )
            raise

    def clear_cache(self) -> None:
        """Clear the components cache."""
        self._components_cache = None
        self._market_cache.clear()


__all__ = ['ComponentLoader']
