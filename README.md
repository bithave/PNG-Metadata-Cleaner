# PNG-Metadata-Cleaner
> 一个轻量级的Python工具，用于批量清除PNG图片中的元数据标签，保护用户隐私。

---

## 📌 开发目的

### 背景
随着AI生成图像技术的普及，各大AI平台（如豆包、Midjourney、DALL-E等）开始在生成的图片中嵌入**AIGC溯源标签**。这些标签包含：
- 生成平台信息
- 用户ID/会话ID
- 生成时间戳
- 其他追踪信息

### 问题
- **隐私泄露风险**：AIGC标签可能暴露用户的AI使用习惯和身份信息
- **无意传播**：用户在社交媒体分享图片时，可能 unaware 地泄露了这些敏感信息
- **平台限制**：某些平台对AI生成内容有特殊政策，元数据暴露可能带来麻烦

### 解决方案
本工具提供**一键式批量清除**功能，帮助用户：
- ✅ 批量处理整个文件夹的PNG图片
- ✅ 完全移除AIGC标签和其他元数据
- ✅ 保留图像质量，只清除文本信息
- ✅ 支持备份和预览，安全可控

---

## ✨ 功能特性

| 功能 | 描述 |
|------|------|
| 🚀 **批量处理** | 支持单个文件或整个目录（含子目录）的批量处理 |
| 🔒 **安全备份** | 可选自动备份原文件（.bak），处理无忧 |
| 👁️ **干运行模式** | 预览将要清除的内容，不实际修改文件 |
| 🎯 **精准清除** | 仅移除元数据，保留图像核心数据（IHDR/IDAT/IEND） |
| 🛡️ **零依赖** | 仅使用Python标准库，无需安装任何第三方包 |
| 📝 **详细日志** | 显示处理进度、文件大小变化、统计信息 |

### 清除的元数据类型

- **tEXt** - 文本块（包括AIGC标签）
- **zTXt** - 压缩文本块
- **iTXt** - 国际化文本块
- **tIME** - 修改时间戳
- **pHYs** - 物理像素尺寸
- **gAMA** - Gamma信息

---

## 📦 安装

### 系统要求
- Python 3.7 或更高版本
- Windows / macOS / Linux

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/png-metadata-cleaner.git
cd png-metadata-cleaner

# 2. 验证Python版本
python --version

# 3. 无需安装依赖，直接运行！
python clean_png_metadata.py --help
```

---

## 🚀 使用说明

### 命令行参数

```bash
python clean_png_metadata.py --input <路径> [选项]
```

| 参数 | 简写 | 必需 | 描述 |
|------|------|------|------|
| `--input` | `-i` | ✅ | 输入路径（文件或目录） |
| `--output` | `-o` | ❌ | 输出路径（文件或目录）。省略则原地覆盖 |
| `--recursive` | | ❌ | 递归处理子目录 |
| `--backup` | | ❌ | 处理前备份原文件 |
| `--dry-run` | | ❌ | 干运行模式，只预览不修改 |

### 使用示例

#### 1️⃣ 干运行（预览模式 - 强烈推荐首次使用）
```bash
python clean_png_metadata.py --input ./my_images --recursive --dry-run
```
输出示例：
```
[1/10] ./my_images/photo1.png -> ./my_images/photo1.png | removed: 1 chunks | 100%
[2/10] ./my_images/photo2.png -> ./my_images/photo2.png | removed: 0 chunks | 200%
...
Summary:
  Total input PNGs: 10
  Total metadata chunks removed: 5
  Dry-run: Yes
```

#### 2️⃣ 处理单个文件（带备份）
```bash
python clean_png_metadata.py --input ./photo.png --backup
```
将生成：
- `photo.png` - 已清除元数据
- `photo.png.bak` - 原文件备份

#### 3️⃣ 批量处理整个目录（带备份）
```bash
python clean_png_metadata.py --input ./my_images --recursive --backup
```

#### 4️⃣ 批量处理并输出到新目录
```bash
python clean_png_metadata.py --input ./original --output ./cleaned --recursive
```
保持原目录不变，清理后的文件输出到 `./cleaned` 目录

#### 5️⃣ 原地处理（无备份，谨慎使用）
```bash
python clean_png_metadata.py --input ./my_images --recursive
```

---

## ⚠️ 注意事项

### 🔴 重要提醒

1. **首次使用务必使用 --dry-run**
   - 预览将要清除的内容
   - 确认无误后再实际执行

2. **重要文件建议使用 --backup**
   - 备份文件将以 `.bak` 扩展名保存
   - 如需恢复，重命名备份文件即可

3. **原地修改不可逆**
   - 不使用 `--backup` 且不提供 `--output` 时，将直接覆盖原文件
   - 操作前请确保有原始备份

### 🛡️ 安全机制

本工具内置**三层安全防护**：

1. **扩展名筛选**：只处理 `.png` 和 `.PNG` 文件
2. **签名验证**：验证PNG文件头（\x89PNG\r\n\x1a\n），非PNG文件直接跳过
3. **异常处理**：任何错误都会捕获并跳过，不会损坏文件

### 🚫 不会处理的文件

- 非 `.png`/`.PNG` 扩展名的文件（txt, exe, jpg等）
- 损坏或无效的PNG文件
- 无元数据可清除的PNG文件

---

## 📊 技术细节

### 工作原理

```
输入PNG文件
    ↓
读取所有chunks
    ↓
筛选chunks：
    - 保留：IHDR（头部）、PLTE（调色板）、IDAT（图像数据）、IEND（结尾）
    - 移除：tEXt、zTXt、iTXt、tIME、pHYs、gAMA（元数据）
    ↓
重新组装PNG文件
    ↓
输出清理后的文件
```

### 图像质量

- ✅ **完全无损**：不修改任何像素数据
- ✅ **CRC校验**：保持数据完整性
- ✅ **文件大小**：通常减小（移除元数据），图像部分不变

---

## 🐛 故障排除

### 常见问题

#### Q: 显示 "Not a valid PNG file"
**原因**：文件扩展名是.png，但实际不是PNG格式
**解决**：忽略此错误，工具会自动跳过这类文件

#### Q: 处理后的文件无法打开
**原因**：极少见的PNG格式兼容性问题
**解决**：使用备份文件恢复，提交issue反馈

#### Q: 某些元数据没有被清除
**原因**：可能存在非标准的元数据chunk
**解决**：联系开发者，提供样本文件以便分析

### 错误代码

| 错误信息 | 含义 | 解决方案 |
|---------|------|---------|
| CRC mismatch | 文件可能损坏 | 跳过该文件或使用备份 |
| Unexpected EOF | 文件不完整 | 跳过该文件 |
| Not a valid PNG | 非PNG文件 | 忽略（自动跳过） |

---

## 🤝 贡献指南

欢迎提交Pull Request和Issue！

### 开发流程

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 代码规范

- 遵循 PEP 8 编码规范
- 添加适当的注释和文档字符串
- 确保通过现有测试

---

## 📄 开源协议

本项目采用 [MIT License](LICENSE) 开源协议。

```
MIT License

Copyright (c) 2025 [Your Name]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
...
```

---

## 🙏 致谢

- 感谢所有测试和反馈的用户
- 感谢开源社区的支持

---

## 📞 联系我们

- GitHub Issues: [https://github.com/bithave/png-metadata-cleaner/issues](https://github.com/bithave/png-metadata-cleaner/issues)
- Email: bithavel@outlook.com

---

**保护隐私，从清除元数据开始。** 🔒

---

*文档版本: 1.0.0*  
*最后更新: 2025-02-12*
