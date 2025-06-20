# 📚 LLMOps 平台 API 文档

![API Status](https://img.shields.io/badge/status-active-brightgreen)
![Version](https://img.shields.io/badge/version-0.1.0-blue)

## 开发指南

1. 安装依赖
```bash
pip install -r requirements.txt
```

2. 配置环境变量
```bash
cp .env.example .env
```

3. 启动开发服务器
```bash
flask run --port 5001
```

| 状态码 | 说明           |
| ------ | -------------- |
| 200    | 成功           |
| 400    | 请求参数错误   |
| 401    | 未授权         |
| 403    | 禁止访问       |
| 404    | 资源不存在     |
| 500    | 服务器内部错误 |

## 