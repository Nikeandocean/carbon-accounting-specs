"""
Phase 5: 语义搜索 MCP Tools

为 citation 和 rule 提供自然语言搜索能力。

实现方式：TF-IDF + 余弦相似度（纯 Python，无需外部依赖）。
对于 spec-driven audit 项目，这已经足够：
- 用户问 "Scope 3 融资排放有哪些要求？" → 找到相关 citation 和 rule
- 用户问 "治理机构披露要求" → 找到 Para 6(a) 相关内容
"""

from __future__ import annotations

import json
import logging
import math
import re
from collections import Counter
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .loader import SpecLoader

logger = logging.getLogger(__name__)

_READ_ANN = ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False,
)


# ============================================================
# 简单 TF-IDF 实现（纯 Python，无外部依赖）
# ============================================================

def _tokenize(text: str) -> list[str]:
    """
    简单分词器：支持中英文混合文本。
    - 英文：按空格和标点分词，转小写
    - 中文：按字分词（bigram）
    """
    # 清理文本
    text = text.lower()
    # 英文单词
    english_words = re.findall(r'[a-z0-9]+(?:\.[a-z0-9]+)*', text)
    # 中文字符 bigrams
    chinese_chars = re.findall(r'[一-鿿]', text)
    chinese_bigrams = [chinese_chars[i] + chinese_chars[i + 1]
                      for i in range(len(chinese_chars) - 1)]
    # 单字也保留（用于短查询）
    return english_words + chinese_bigrams + chinese_chars


def _compute_tf(tokens: list[str]) -> dict[str, float]:
    """计算词频（TF）"""
    counter = Counter(tokens)
    total = len(tokens)
    if total == 0:
        return {}
    return {t: c / total for t, c in counter.items()}


def _compute_idf(documents: list[list[str]]) -> dict[str, float]:
    """计算逆文档频率（IDF）"""
    n_docs = len(documents)
    if n_docs == 0:
        return {}
    df = Counter()
    for doc in documents:
        unique_tokens = set(doc)
        for token in unique_tokens:
            df[token] += 1
    return {t: math.log((n_docs + 1) / (count + 1)) + 1 for t, count in df.items()}


def _tfidf_vector(tf: dict[str, float], idf: dict[str, float]) -> dict[str, float]:
    """计算 TF-IDF 向量"""
    return {t: tf_val * idf.get(t, 1.0) for t, tf_val in tf.items()}


def _cosine_similarity(v1: dict[str, float], v2: dict[str, float]) -> float:
    """计算余弦相似度"""
    common = set(v1.keys()) & set(v2.keys())
    if not common:
        return 0.0
    dot = sum(v1[k] * v2[k] for k in common)
    norm1 = math.sqrt(sum(v ** 2 for v in v1.values()))
    norm2 = math.sqrt(sum(v ** 2 for v in v2.values()))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


class SemanticIndex:
    """
    轻量级语义索引：基于 TF-IDF 的文本检索。
    支持增量构建和查询。
    """

    def __init__(self):
        self.documents: list[dict] = []  # {id, text, metadata, tokens}
        self.idf: dict[str, float] = {}
        self.vectors: list[dict[str, float]] = []

    def add_document(self, doc_id: str, text: str, metadata: dict = None):
        """添加文档到索引"""
        tokens = _tokenize(text)
        self.documents.append({
            "id": doc_id,
            "text": text,
            "metadata": metadata or {},
            "tokens": tokens,
        })

    def build(self):
        """构建 TF-IDF 索引"""
        all_tokens = [doc["tokens"] for doc in self.documents]
        self.idf = _compute_idf(all_tokens)
        self.vectors = []
        for doc in self.documents:
            tf = _compute_tf(doc["tokens"])
            vec = _tfidf_vector(tf, self.idf)
            self.vectors.append(vec)

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """
        搜索最相关的文档。

        Args:
            query: 查询文本
            top_k: 返回前 k 个结果

        Returns:
            排序后的结果列表，每项包含 {id, score, text, metadata}
        """
        query_tokens = _tokenize(query)
        query_tf = _compute_tf(query_tokens)
        query_vec = _tfidf_vector(query_tf, self.idf)

        scored = []
        for i, doc_vec in enumerate(self.vectors):
            score = _cosine_similarity(query_vec, doc_vec)
            if score > 0:
                scored.append({
                    "id": self.documents[i]["id"],
                    "score": round(score, 4),
                    "text": self.documents[i]["text"],
                    "metadata": self.documents[i]["metadata"],
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]


# ============================================================
# 全局索引缓存
# ============================================================

_citation_index: SemanticIndex | None = None
_rule_index: SemanticIndex | None = None


def _get_citation_index(loader: SpecLoader) -> SemanticIndex:
    """获取或构建 citation 语义索引"""
    global _citation_index
    if _citation_index is not None:
        return _citation_index

    index = SemanticIndex()
    for path, spec in loader.specs.items():
        meta = spec.get("meta", {})
        source = meta.get("source", path)
        for cit in spec.get("citations", []):
            cit_id = cit.get("id", "")
            text = cit.get("text", "")
            section = cit.get("section", "")
            # 索引文本 = section + text
            full_text = f"{section} {text}"
            index.add_document(
                doc_id=cit_id,
                text=full_text,
                metadata={
                    "spec_path": path,
                    "source": source,
                    "section": section,
                    "citation_id": cit_id,
                },
            )
    index.build()
    _citation_index = index
    return _citation_index


def _get_rule_index(loader: SpecLoader) -> SemanticIndex:
    """获取或构建 rule 语义索引"""
    global _rule_index
    if _rule_index is not None:
        return _rule_index

    index = SemanticIndex()
    for path, spec in loader.specs.items():
        meta = spec.get("meta", {})
        source = meta.get("source", path)
        for rule in spec.get("rules", []):
            if rule.get("layer") == "knowledge":
                continue
            rule_id = rule.get("id", "")
            name = rule.get("name", "")
            on_fail_msg = rule.get("on_fail_message", "")
            # 索引文本 = name + on_fail_message
            full_text = f"{name} {on_fail_msg}"
            index.add_document(
                doc_id=rule_id,
                text=full_text,
                metadata={
                    "spec_path": path,
                    "source": source,
                    "rule_id": rule_id,
                    "severity": rule.get("severity", ""),
                    "lifecycle": rule.get("lifecycle", ""),
                    "citation": rule.get("citation", ""),
                },
            )
    index.build()
    _rule_index = index
    return _rule_index


# ============================================================
# MCP Tool 注册
# ============================================================

def register_search_tools(mcp: FastMCP, loader: SpecLoader) -> None:
    """注册语义搜索 MCP 工具"""

    @mcp.tool(annotations=_READ_ANN)
    async def search_citations(
        query: str,
        spec_id: str = "",
        top_k: int = 10,
    ) -> str:
        """
        用自然语言搜索 citation（标准引用原文）。

        适用于：
        - 用户问 "有哪些关于 Scope 3 融资排放的要求？"
        - 用户问 "治理机构披露的相关规定"
        - 用户问 "气候情景分析的标准引用"

        Args:
            query: 自然语言查询（中英文均可）
            spec_id: 可选，限制在某个 spec 内搜索
            top_k: 返回前 k 个结果（默认 10）

        Returns:
            JSON 字符串，包含匹配的 citation 列表
        """
        try:
            index = _get_citation_index(loader)
            results = index.search(query, top_k=top_k * 2)  # 多取一些用于过滤

            # 如果指定了 spec_id，过滤结果
            if spec_id:
                results = [
                    r for r in results
                    if spec_id in r["metadata"].get("spec_path", "")
                ]

            results = results[:top_k]

            return json.dumps({
                "query": query,
                "total_results": len(results),
                "results": results,
            }, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.exception("search_citations failed")
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @mcp.tool(annotations=_READ_ANN)
    async def search_rules(
        query: str,
        spec_id: str = "",
        severity: str = "",
        top_k: int = 10,
    ) -> str:
        """
        用自然语言搜索规则（rules）。

        适用于：
        - 用户问 "有哪些关于排放披露的规则？"
        - 用户问 "治理相关的强制要求"
        - 用户问 "pre_calculation 阶段的规则"

        Args:
            query: 自然语言查询
            spec_id: 可选，限制在某个 spec 内搜索
            severity: 可选，按严重级别过滤（fatal/warning/info）
            top_k: 返回前 k 个结果

        Returns:
            JSON 字符串，包含匹配的规则列表
        """
        try:
            index = _get_rule_index(loader)
            results = index.search(query, top_k=top_k * 3)

            # 过滤
            if spec_id:
                results = [
                    r for r in results
                    if spec_id in r["metadata"].get("spec_path", "")
                ]
            if severity:
                results = [
                    r for r in results
                    if r["metadata"].get("severity", "") == severity
                ]

            results = results[:top_k]

            # 补充完整规则信息
            enriched = []
            for r in results:
                rule_id = r["metadata"].get("rule_id", r["id"])
                rule = loader.get_rule(rule_id)
                if rule:
                    enriched.append({
                        "rule_id": rule_id,
                        "score": r["score"],
                        "name": rule.get("name", ""),
                        "severity": rule.get("severity", ""),
                        "lifecycle": rule.get("lifecycle", ""),
                        "on_fail": rule.get("on_fail", ""),
                        "on_fail_message": rule.get("on_fail_message", ""),
                        "citation": rule.get("citation", ""),
                    })
                else:
                    enriched.append({
                        "rule_id": rule_id,
                        "score": r["score"],
                        "metadata": r["metadata"],
                    })

            return json.dumps({
                "query": query,
                "total_results": len(enriched),
                "results": enriched,
            }, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.exception("search_rules failed")
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @mcp.tool(annotations=_READ_ANN)
    async def search_all(
        query: str,
        spec_id: str = "",
        top_k: int = 5,
    ) -> str:
        """
        综合搜索：同时搜索 citations 和 rules。

        这是最通用的搜索工具，当你不确定该搜 citations 还是 rules 时使用。

        Args:
            query: 自然语言查询
            spec_id: 可选，限制在某个 spec 内
            top_k: 每类返回前 k 个结果

        Returns:
            JSON 字符串，包含 citations 和 rules 的搜索结果
        """
        try:
            # 搜索 citations
            cit_index = _get_citation_index(loader)
            cit_results = cit_index.search(query, top_k=top_k * 2)
            if spec_id:
                cit_results = [
                    r for r in cit_results
                    if spec_id in r["metadata"].get("spec_path", "")
                ]
            cit_results = cit_results[:top_k]

            # 搜索 rules
            rule_index = _get_rule_index(loader)
            rule_results = rule_index.search(query, top_k=top_k * 2)
            if spec_id:
                rule_results = [
                    r for r in rule_results
                    if spec_id in r["metadata"].get("spec_path", "")
                ]
            rule_results = rule_results[:top_k]

            # 补充规则信息
            enriched_rules = []
            for r in rule_results:
                rule_id = r["metadata"].get("rule_id", r["id"])
                rule = loader.get_rule(rule_id)
                if rule:
                    enriched_rules.append({
                        "rule_id": rule_id,
                        "score": r["score"],
                        "name": rule.get("name", ""),
                        "severity": rule.get("severity", ""),
                        "on_fail_message": rule.get("on_fail_message", ""),
                    })

            return json.dumps({
                "query": query,
                "citations": cit_results,
                "rules": enriched_rules,
            }, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.exception("search_all failed")
            return json.dumps({"error": str(e)}, ensure_ascii=False)
