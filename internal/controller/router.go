package controller

import (
	"github.com/gin-gonic/gin"
	"github.com/langgenius/dify-sandbox/internal/middleware"
	"github.com/langgenius/dify-sandbox/internal/static"
	"net/http"
)

func Setup(Router *gin.Engine) {
	PublicGroup := Router.Group("")
	PrivateGroup := Router.Group("/v1/sandbox/")

	PrivateGroup.Use(middleware.Auth())

	{
		// health check
		PublicGroup.GET("/health", func(c *gin.Context) {
			c.JSON(http.StatusOK, "ok")
		})
	}

	//InitRunRouter(PrivateGroup)
	//InitDependencyRouter(PrivateGroup)
}

