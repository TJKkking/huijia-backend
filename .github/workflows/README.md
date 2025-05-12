# GitHub Actions 工作流说明

## Django CI 工作流

### 触发条件
- 推送到 `main` 或 `develop` 分支
- 创建 Pull Request 到 `main` 或 `develop` 分支

### 工作流程
1. **环境准备**
   - 使用 Ubuntu 最新版
   - 设置 Python 3.10
   - 启动 PostgreSQL 15 服务

2. **缓存优化**
   - pip 依赖缓存
   - Python 包缓存
   - 测试结果缓存

3. **测试执行**
   - 安装项目依赖
   - 运行数据库迁移
   - 执行测试并生成覆盖率报告
   - 上传覆盖率报告到 Codecov

### 环境变量
- `POSTGRES_DB`: 测试数据库名
- `POSTGRES_USER`: 数据库用户名
- `POSTGRES_PASSWORD`: 数据库密码
- `DJANGO_SETTINGS_MODULE`: Django 设置模块
- `SECRET_KEY`: Django 密钥
- `DEBUG`: 调试模式开关

### 缓存策略
1. **pip 依赖缓存**
   - 路径: `~/.cache/pip`
   - 键: 基于 requirements.txt 的哈希值

2. **Python 包缓存**
   - 路径: Python 包安装目录
   - 键: 基于 requirements.txt 的哈希值

3. **测试结果缓存**
   - 路径: pytest 缓存和覆盖率报告
   - 键: 基于 requirements.txt 和测试文件的哈希值

### 注意事项
1. 确保 requirements.txt 包含所有必要的依赖
2. 测试文件变化会导致测试结果缓存失效
3. 覆盖率报告会上传到 Codecov 进行可视化展示 