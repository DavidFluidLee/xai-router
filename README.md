
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



(base) davidlee@H-00949 test % python system_status_report.py
🚀 网关系统 - 最终状态报告
============================================================
生成时间: 2025-10-19 17:47:08

🔧 系统基本信息
------------------------------
   状态: healthy
   Redis状态: Unknown
   时间戳: 1760867228

📊 配置版本信息
------------------------------
   全局版本: 1760866897613493000
   最后更新: 1760866897613493000
   内存路由数: 6
   Redis路由数: 6
   实例ID: instance-1760867222704327000
   Redis启用: True

🌊 事件系统状态
------------------------------
   总事件数: 0
   待处理数: 0
   消费者组数: 0
   事件流长度: 78

🛣️ 当前路由列表
------------------------------
   总路由数: 6
    1. critical-payment
       路径: /api/payment/process
       方法: POST
       处理器: sandbox
    2. event-delete-test
       路径: /api/event-delete
       方法: GET
       处理器: sandbox
    3. direct-execute
       路径: /execute
       方法: POST
       处理器: sandbox
    4. status-simple
       路径: /status
       方法: GET
       处理器: sandbox
    5. math-simple
       路径: /math
       方法: POST
       处理器: sandbox
    6. calculate-simple
       路径: /calculate
       方法: POST
       处理器: sandbox

🔧 可用管理接口
------------------------------
   GET    /admin/health                  - 健康检查
   GET    /admin/routes                  - 路由列表
   POST   /admin/routes                  - 创建路由
   PUT    /admin/routes/:id              - 更新路由
   DELETE /admin/routes/:id              - 删除路由
   GET    /admin/config/version          - 配置版本
   GET    /admin/events/stats            - 事件统计
   GET    /admin/events/stream-info      - 事件流信息
   GET    /admin/events/consumers        - 事件消费者
   POST   /admin/sync/trigger            - 手动同步
   GET    /admin/routes/:routeId/details - 路由详情
   POST   /admin/events/cleanup          - 事件清理

🎯 系统总结
------------------------------
   ✅ 路由同步: 完美同步
   ✅ 管理接口: 全部正常
   📍 管理端口: 8081
   📍 网关端口: 8080

🎉 系统状态: 健康运行中
