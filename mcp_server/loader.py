"""
YAML 规范文件加载器

按 _meta.yaml 的 load_order 加载所有 spec 文件，
并构建 citation 索引供快速查询。
"""

from __future__ import annotations
from pathlib import Path
from typing import Any
import yaml


class SpecLoader:
    """加载和管理 YAML 规范文件"""

    def __init__(self, spec_dir: str | Path):
        self.spec_dir = Path(spec_dir)
        self.meta: dict[str, Any] = {}
        self.specs: dict[str, Any] = {}
        self._citation_index: dict[str, tuple[str, str]] = {}  # cit_id -> (spec_path, text)

    def load_all(self) -> None:
        """按 load_order 加载全部 spec 文件，并自动发现新目录下的 spec"""
        meta_path = self.spec_dir / "_meta.yaml"
        if not meta_path.exists():
            raise FileNotFoundError(f"找不到 _meta.yaml: {meta_path}")

        with open(meta_path, encoding="utf-8") as f:
            self.meta = yaml.safe_load(f)

        # 1. 按 load_order 加载已有 spec
        loaded_paths = set()
        for path in self.meta.get("load_order", []):
            file_path = self.spec_dir / f"{path}.yaml"
            if file_path.exists():
                with open(file_path, encoding="utf-8") as f:
                    spec = yaml.safe_load(f)
                    self.specs[path] = spec
                    loaded_paths.add(path)
                    self._index_citations(path, spec)

        # 2. 自动发现 load_order 之外的 spec 文件（如 green-finance/）
        for yaml_file in sorted(self.spec_dir.rglob("*.yaml")):
            if yaml_file.name == "_meta.yaml":
                continue
            rel = yaml_file.relative_to(self.spec_dir).with_suffix("")
            path_key = str(rel).replace("\\", "/")
            if path_key not in loaded_paths:
                with open(yaml_file, encoding="utf-8") as f:
                    spec = yaml.safe_load(f)
                    if spec and (spec.get("rules") or spec.get("meta")):
                        self.specs[path_key] = spec
                        self._index_citations(path_key, spec)

    def load_scope(self, scope: str) -> dict[str, Any]:
        """加载指定 scope 的 spec 文件（如 'scope1', 'scope3'）"""
        result = {}
        for path, spec in self.specs.items():
            if path.startswith(scope) or path.startswith(f"{scope}/"):
                result[path] = spec
        return result

    def load_domain(self, domain: str) -> dict[str, Any]:
        """加载指定域的 spec 文件（如 'green-finance'）"""
        result = {}
        for path, spec in self.specs.items():
            if domain in path:
                result[path] = spec
        return result

    def get_rule(self, rule_id: str) -> dict[str, Any] | None:
        """按 rule_id 查找规则"""
        for spec in self.specs.values():
            for rule in spec.get("rules", []):
                if rule.get("id") == rule_id:
                    return rule
        return None

    def get_citation(self, cit_id: str) -> dict[str, str] | None:
        """按 citation ID 查找引用原文"""
        if cit_id in self._citation_index:
            spec_path, text = self._citation_index[cit_id]
            return {"id": cit_id, "spec": spec_path, "text": text}
        # 遍历所有 spec 的 citations
        for path, spec in self.specs.items():
            for cit in spec.get("citations", []):
                if cit.get("id") == cit_id:
                    return {"id": cit_id, "spec": path, "text": cit.get("text", "")}
        return None

    def list_rules(self, scope: str | None = None, lifecycle: str | None = None) -> list[dict]:
        """列出规则，可按 scope 和 lifecycle 过滤"""
        rules = []
        for path, spec in self.specs.items():
            if scope and not (path.startswith(scope) or scope in path):
                continue
            for rule in spec.get("rules", []):
                if rule.get("layer") == "knowledge":
                    continue
                if lifecycle and rule.get("lifecycle") != lifecycle:
                    continue
                rules.append({
                    "id": rule.get("id"),
                    "name": rule.get("name"),
                    "severity": rule.get("severity"),
                    "lifecycle": rule.get("lifecycle"),
                    "spec": path,
                })
        return rules

    def _index_citations(self, spec_path: str, spec: dict) -> None:
        """构建 citation 索引"""
        for cit in spec.get("citations", []):
            cit_id = cit.get("id")
            if cit_id:
                self._citation_index[cit_id] = (spec_path, cit.get("text", ""))

    @property
    def stats(self) -> dict[str, int]:
        """统计信息"""
        total_rules = 0
        total_citations = 0
        for spec in self.specs.values():
            rules = spec.get("rules", [])
            total_rules += sum(1 for r in rules if r.get("layer") != "knowledge")
            total_citations += len(spec.get("citations", []))
        return {
            "spec_files": len(self.specs),
            "rules": total_rules,
            "citations": total_citations,
        }
