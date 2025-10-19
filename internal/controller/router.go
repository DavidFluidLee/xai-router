package controller

// import (
// 	"github.com/gin-gonic/gin"
// 	"github.com/langgenius/dify-sandbox/internal/middleware"
// 	"github.com/langgenius/dify-sandbox/internal/static"
// 	"net/http"
// )

// func Setup(Router *gin.Engine) {
// 	PublicGroup := Router.Group("")
// 	SandboxGroup := Router.Group("/v1/sandbox")

// 	// 沙箱接口使用网关认证
// 	SandboxGroup.Use(middleware.GatewayAuth())

// 	{
// 		// 健康检查 - 公共接口
// 		PublicGroup.GET("/health", func(c *gin.Context) {
// 			c.JSON(http.StatusOK, gin.H{
// 				"status":  "ok",
// 				"service": "xai-sandbox",
// 			})
// 		})

// 		// 服务信息 - 公共接口
// 		PublicGroup.GET("/info", func(c *gin.Context) {
// 			c.JSON(http.StatusOK, gin.H{
// 				"name":        "xai-sandbox",
// 				"description": "AI Sandbox Environment",
// 				"status":      "running",
// 			})
// 		})
// 	}

// 	// 初始化沙箱路由
// 	InitSandboxRouter(SandboxGroup)
	
// 	// 初始化内部管理路由
// 	InitInternalRouter(Router)
// }

// func InitSandboxRouter(Router *gin.RouterGroup) {
// 	// 运行沙箱代码
// 	Router.POST("/run",
// 		middleware.MaxRequest(static.GetDifySandboxGlobalConfigurations().MaxRequests),
// 		middleware.MaxWorker(static.GetDifySandboxGlobalConfigurations().MaxWorkers),
// 		RunSandboxController,
// 	)
	
// 	// 沙箱状态
// 	Router.GET("/status", GetSandboxStatus)
// }

// func InitInternalRouter(Router *gin.Engine) {
// 	// 内部管理接口组
// 	InternalGroup := Router.Group("/internal")
// 	InternalGroup.Use(middleware.AdminAuth())
// 	{
// 		// 依赖管理接口
// 		deps := InternalGroup.Group("/dependencies")
// 		{
// 			deps.GET("", GetDependencies)
// 			deps.POST("/update", UpdateDependencies)
// 			deps.GET("/refresh", RefreshDependencies)
// 		}

// 		// 管理接口
// 		management := InternalGroup.Group("/management")
// 		{
// 			management.GET("/config", GetSandboxConfig)
// 			management.GET("/metrics", GetSandboxMetrics)
// 		}
// 	}
// }

// // 控制器函数
// func GetSandboxStatus(c *gin.Context) {
// 	c.JSON(200, gin.H{
// 		"workers": static.GetDifySandboxGlobalConfigurations().MaxWorkers,
// 		"requests": static.GetDifySandboxGlobalConfigurations().MaxRequests,
// 		"status": "active",
// 	})
// }

// func GetSandboxConfig(c *gin.Context) {
// 	c.JSON(501, gin.H{"error": "sandbox management not implemented yet"})
// }

// func GetSandboxMetrics(c *gin.Context) {
// 	c.JSON(501, gin.H{"error": "sandbox metrics not implemented yet"})
// }