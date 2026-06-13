# 贡献指南

感谢你对本项目的关注！我们欢迎各种形式的贡献。

## 如何贡献

### 1. 添加排放因子数据

如果你所在国家/地区的排放因子数据缺失，请：

1. 点击 [New Issue](../../issues/new/choose)
2. 选择 "添加排放因子数据" 模板
3. 填写相关信息

### 2. 报告规则错误

如果发现规则逻辑错误，请：

1. 点击 [New Issue](../../issues/new/choose)
2. 描述问题和预期行为
3. 附上 GHG Protocol 原文引用（如有）

### 3. 改进翻译

如果发现中文翻译不准确：

1. Fork 本仓库
2. 修改对应的 YAML 文件
3. 提交 Pull Request

### 4. 提出新规则建议

如果你认为需要新增规则：

1. 点击 [New Issue](../../issues/new/choose)
2. 说明规则的必要性
3. 附上 GHG Protocol 原文引用

## 开发流程

### Fork & Clone

```bash
# Fork 仓库后
git clone https://github.com/YOUR_USERNAME/carbon-accounting-specs.git
cd carbon-accounting-specs
```

### 创建分支

```bash
git checkout -b feature/your-feature-name
```

### 提交规范

提交信息格式：
```
<type>: <description>

[optional body]

[optional footer]
```

类型：
- `feat`: 新功能
- `fix`: 修复错误
- `docs`: 文档更新
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具

示例：
```
feat: add emission factor for Japan (2024)

- Added grid average emission factor: 0.4532 tCO2/MWh
- Source: Ministry of the Environment, Japan
- URL: https://www.env.go.jp/en/
```

### 提交 Pull Request

1. 确保所有 YAML 文件格式正确
2. 更新相关文档
3. 描述你的改动和原因
4. 关联相关 Issue

## 规则编写规范

### 文件结构

每个 YAML 文件必须包含：
- `meta`: 元数据（id, version, source, layer）
- `citations`: GHG Protocol 原文引用
- `rules`: 规则定义

### 规则格式

```yaml
- id: "rule-xxx"
  name: "规则名称"
  type: "requirement | constraint | recommendation"
  priority: "MUST | SHOULD | MAY"
  severity: "fatal | warning | info"
  layer: "schema | knowledge | hybrid"
  lifecycle: "pre_calculation | runtime_inference | post_audit"
  assertion: <JsonLogic expression>
  on_fail: "raise_fatal | raise_warning | log_info | require_justification"
  on_fail_message: "失败提示"
  citation: "引用ID"
```

### 引用格式

```yaml
citations:
  - id: "cit-xxx"
    text: "原文段落"
    page: <页码>
    section: "章节名称"
```

## 行为准则

- 尊重所有贡献者
- 基于事实和标准讨论
- 保持专业和友善

## 问题？

如有疑问，请在 [Discussion](../../discussions) 中提问。
