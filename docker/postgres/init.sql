-- 检测postgres是否未安装uuid扩展 如果未安装则安装
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";