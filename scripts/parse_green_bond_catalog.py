#!/usr/bin/env python3
"""解析绿色债券支持项目目录 PDF 文本，生成 YAML 规范文件。"""

import re
import yaml
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def parse_catalog(text: str) -> dict:
    lines = text.split('\n')

    # Step 1: 去重（PDF 4列表头导致每行重复4次）
    deduped = []
    prev = None
    count = 0
    for line in lines:
        line = line.strip()
        if line == prev:
            count += 1
            if count <= 1:  # 允许最多重复1次
                deduped.append(line)
        else:
            deduped.append(line)
            count = 0
        prev = line

    # Step 2: 去除页面标记和表头
    skip_exact = {'领域', '项目名称', '说明', '说明/条件', '条件', '附件'}
    cleaned = []
    for line in deduped:
        if not line:
            continue
        if re.match(r'^=== PAGE \d+ ===$', line):
            continue
        if re.match(r'^— \d+ —$', line):
            continue
        if line in skip_exact:
            continue
        cleaned.append(line)

    # Step 3: 合并断行
    # 规则：以数字编号开头的行是新分类，其余是上一行的延续
    code_re = re.compile(r'^(\d+\.\d+(?:\.\d+){0,3})\s+(.*?)$')
    top_re = re.compile(r'^([一二三四五六])、(.*)$')

    merged = []
    for line in cleaned:
        if code_re.match(line) or top_re.match(line):
            merged.append(line)
        elif merged:
            merged[-1] += line

    # Step 4: 先从非合并行提取分类名称（短行）
    # 非合并的原始行中有独立的分类名行
    code_re2 = re.compile(r'^(\d+\.\d+(?:\.\d+){0,3})\s+(.+)$')
    name_map = {}  # code -> name (从短行中提取)
    for line in cleaned:
        m = code_re2.match(line)
        if m:
            code = m.group(1)
            name = m.group(2).strip()
            # 短行是纯名称（没有描述），长行是名称+描述合并
            if len(name) < 20 and not any(c in name for c in '，。（'):
                name_map[code] = name

    # Step 5: 解析分类结构
    categories = {}
    num_map = {'一': '1', '二': '2', '三': '3', '四': '4', '五': '5', '六': '6'}

    for line in merged:
        m = top_re.match(line)
        if m:
            code = num_map[m.group(1)]
            categories[code] = {
                'code': code, 'name': m.group(2).strip(), 'level': 1, 'desc': ''
            }
            continue

        m = code_re.match(line)
        if m:
            code = m.group(1)
            rest = m.group(2).strip()
            level = code.count('.') + 1

            # 用 name_map 分离 name 和 description
            known_name = name_map.get(code, '')
            if known_name and rest.startswith(known_name):
                name = known_name
                desc = rest[len(known_name):].strip()
            else:
                # 启发式：name 是前 N 个中文字符
                name_match = re.match(r'^([一-鿿（）、/]{2,15})', rest)
                if name_match:
                    name = name_match.group(1)
                    desc = rest[name_match.end():].strip()
                else:
                    name = rest[:20]
                    desc = rest[20:]

            categories[code] = {
                'code': code, 'name': name.strip(), 'level': level, 'desc': desc.strip()
            }

    # 提取 GB 标准引用
    for cat in categories.values():
        cat['gb_refs'] = re.findall(r'《([^》]+)》（(GB[/\w\s\-]+?)）', cat.get('desc', ''))

    return categories


def generate_yaml(categories: dict) -> str:
    top_cats = {v['code']: v['name'] for v in categories.values() if v['level'] == 1}
    valid_codes = sorted([c['code'] for c in categories.values() if c['level'] >= 3])

    # Citations
    citations = []
    for i, (code, cat) in enumerate(sorted(categories.items()), 1):
        if cat['level'] >= 3 and cat['desc']:
            text = f"{cat['name']}：{cat['desc'][:300]}"
            if cat.get('gb_refs'):
                text += f" [技术标准: {', '.join(r[1] for r in cat['gb_refs'])}]"
            citations.append({
                'id': f'cit-gb-{i:03d}',
                'text': text,
                'section': f'绿色债券目录 {code}',
            })

    # Rules
    rules = [
        {
            'id': 'gbc-001',
            'name': '项目类别代码有效性校验',
            'type': 'requirement',
            'priority': 'MUST',
            'severity': 'fatal',
            'layer': 'schema',
            'lifecycle': 'pre_calculation',
            'condition': {'!=': [{'var': 'input.project.category_code'}, None]},
            'assertion': {'in': [{'var': 'input.project.category_code'}, valid_codes]},
            'on_fail': 'raise_fatal',
            'on_fail_message': f'项目类别代码不在绿色债券目录有效范围内（共{len(valid_codes)}个有效代码）',
        },
        {
            'id': 'gbc-002',
            'name': '项目名称必填校验',
            'type': 'requirement',
            'priority': 'MUST',
            'severity': 'fatal',
            'layer': 'schema',
            'lifecycle': 'pre_calculation',
            'assertion': {'and': [
                {'!=': [{'var': 'input.project.project_name'}, None]},
                {'!=': [{'var': 'input.project.project_name'}, '']},
            ]},
            'on_fail': 'raise_fatal',
            'on_fail_message': '缺少必填字段：项目名称',
        },
        {
            'id': 'gbc-003',
            'name': '项目类别代码必填校验',
            'type': 'requirement',
            'priority': 'MUST',
            'severity': 'fatal',
            'layer': 'schema',
            'lifecycle': 'pre_calculation',
            'assertion': {'!=': [{'var': 'input.project.category_code'}, None]},
            'on_fail': 'raise_fatal',
            'on_fail_message': '缺少必填字段：项目类别代码',
        },
        {
            'id': 'gbc-004',
            'name': '募集资金用途校验',
            'type': 'requirement',
            'priority': 'MUST',
            'severity': 'fatal',
            'layer': 'schema',
            'lifecycle': 'pre_calculation',
            'condition': {'!=': [{'var': 'input.bond'}, None]},
            'assertion': {'in': [{'var': 'input.bond.fund_usage'}, ['green_project', 'green_refinancing']]},
            'on_fail': 'raise_fatal',
            'on_fail_message': '绿色债券募集资金应100%用于符合条件的绿色项目',
        },
        {
            'id': 'gbc-005',
            'name': '环境效益信息披露',
            'type': 'requirement',
            'priority': 'SHOULD',
            'severity': 'warning',
            'layer': 'schema',
            'lifecycle': 'post_audit',
            'assertion': {'!=': [{'var': 'input.project.environmental_benefit'}, None]},
            'on_fail': 'raise_warning',
            'on_fail_message': '应披露绿色项目的预计环境效益',
        },
    ]

    doc = {
        'meta': {
            'id': 'green-finance/bond-catalog',
            'version': '2.0.0',
            'source': '《绿色债券支持项目目录（2021年版）》',
            'source_ref': '中国人民银行、国家发展改革委、证监会 银发〔2021〕96号',
            'layer': 'schema',
            'description': f'绿色债券支持项目目录。{len(categories)} 个项目分类，{len(citations)} 条原文引用，{len(rules)} 条规则。',
        },
        'citations': citations,
        'rules': rules,
        'catalog_summary': {
            'top_level': top_cats,
            'total_categories': len(categories),
            'valid_project_codes': len(valid_codes),
        },
    }
    return yaml.dump(doc, allow_unicode=True, default_flow_style=False, sort_keys=False, width=120)


def main():
    text = Path('specs/green-finance/green-bond-catalog-text.txt').read_text(encoding='utf-8')
    categories = parse_catalog(text)
    yaml_content = generate_yaml(categories)
    Path('specs/green-finance/bond-catalog.yaml').write_text(yaml_content, encoding='utf-8')

    data = yaml.safe_load(yaml_content)
    print(f'Categories: {len(categories)}')
    print(f'Valid codes: {data["catalog_summary"]["valid_project_codes"]}')
    print(f'Citations: {len(data["citations"])}')
    print(f'Rules: {len(data["rules"])}')

    # Show sample citations
    for c in data['citations'][:3]:
        print(f'  {c["id"]}: {c["text"][:80]}...')


if __name__ == '__main__':
    main()
