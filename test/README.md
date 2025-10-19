# Python测试
python3 test_config_version.py
python3 test_route_management.py  
python3 test_performance.py

# Shell集成测试
chmod +x test_integration.sh
./test_integration.sh



(base) davidlee@H-00949 test % curl -H "X-Api-Key: xai-admin-key" http://localhost:8195/admin/health
{"routes":6,"sandboxes":1,"status":"healthy","timestamp":1760895004}%
