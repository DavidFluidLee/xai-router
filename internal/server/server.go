package server

import (
	"fmt"

	"github.com/gin-gonic/gin"
	"github.com/langgenius/dify-sandbox/internal/gateway"
	"github.com/langgenius/dify-sandbox/internal/static"
	"github.com/langgenius/dify-sandbox/internal/utils/log"
)

func initConfig() {
	// 初始化配置
	err := static.InitConfig("conf/config.yaml")
	if err != nil {
		log.Panic("failed to init config: %v", err)
	}
	log.Info("config init success")
}

func initGatewayServer() {
	config := static.GetDifySandboxGlobalConfigurations()
	
	// 设置Gin模式
	if !config.App.Debug {
		gin.SetMode(gin.ReleaseMode)
	}

	// 创建分布式路由器，传入 Redis 地址和密码
	router := gateway.NewDistributedRouter(config.Redis.Addr, config.Redis.Password)
	
	// 设置负载均衡策略
	router.SetLoadBalancerStrategy(config.Gateway.LoadBalancerStrategy)
	
	// 设置端口
	router.SetPorts(config.Gateway.Port, config.Gateway.Port+1)

	// 启动网关服务器
	addr := fmt.Sprintf(":%d", config.Gateway.Port)
	log.Info("Starting gateway server on " + addr)
	log.Info("Load balancer strategy: %s", config.Gateway.LoadBalancerStrategy)
	log.Info("Health check interval: %d seconds", config.Gateway.HealthCheckInterval)
	log.Info("Redis address: %s", config.Redis.Addr)
	
	if err := router.Run(addr); err != nil {
		log.Panic("Failed to start gateway server: %v", err)
	}
}

func Run() {
	// 初始化配置
	initConfig()
	
	// 启动网关服务器
	initGatewayServer()
}
