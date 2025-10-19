
# xai-router
XAI Router Gateway

go build -o main -ldflags="-s -w" cmd/server/main.go



CREATE: POST /admin/routes
READ: GET /admin/routes
UPDATE: PUT /admin/routes/:id
DELETE: DELETE /admin/routes/:id




1. 完整测试

# 给脚本执行权限
chmod +x test_gateway_crud.sh
chmod +x test_individual_operations.sh

# 运行完整测试
./test_gateway_crud.sh


2. 单独功能测试

# 健康检查
./test_individual_operations.sh health

# 查看路由
./test_individual_operations.sh routes

# 创建测试路由
./test_individual_operations.sh create

# 测试路由执行  
./test_individual_operations.sh test

# 更新路由
./test_individual_operations.sh update

# 删除路由
./test_individual_operations.sh delete

# 负载测试
./test_individual_operations.sh load



测试覆盖的功能

✅ 健康检查 - 系统状态监控
✅ 路由 CRUD - 完整的创建、读取、更新、删除
✅ 路由执行 - 代码在沙箱中正确执行
✅ 错误处理 - 无效路由、错误方法等
✅ 沙箱管理 - 注册、查看、删除沙箱实例
✅ 负载均衡 - 请求分配到不同沙箱实例
✅ 数据持久化 - Redis 存储路由配置

这些测试用例可以全面验证你的 XAI Router Gateway 的所有功能




启动成功状态

从日志可以看到：

🚀 服务状态

网关服务器: 运行在 :8080
管理API: 运行在 :8081
Redis连接: ✅ 成功
事件消费者: ✅ 已启动
路由加载: 4个路由已从Redis加载
🔄 系统运行正常

健康检查正常运行（每15秒）
配置监听正常运行（每10秒检查更新）
事件消费者后台运行




curl http://localhost:8081/admin/events/stream-info
