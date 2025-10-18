package server

import (
	"fmt"

	"github.com/gin-gonic/gin"
	//"github.com/langgenius/dify-sandbox/internal/controller"
	//"github.com/langgenius/dify-sandbox/internal/core/runner/python"
	"github.com/langgenius/dify-sandbox/internal/static"
	"github.com/langgenius/dify-sandbox/internal/utils/log"
)

func initConfig() {
	// auto migrate database
	err := static.InitConfig("conf/config.yaml")
	if err != nil {
		log.Panic("failed to init config: %v", err)
	}
	log.Info("config init success")

	if err != nil {
		log.Error("failed to setup runner dependencies: %v", err)
	}
	log.Info("runner dependencies init success")
}

func initServer() {
	config := static.GetDifySandboxGlobalConfigurations()
	if !config.App.Debug {
		gin.SetMode(gin.ReleaseMode)
	}

	r := gin.Default()
	r.Use(gin.Recovery())
	if gin.Mode() == gin.DebugMode {
		r.Use(gin.Logger())
	}


	r.Run(fmt.Sprintf(":%d", config.App.Port))
}

func initDependencies() {
	log.Info("installing python dependencies...")
	log.Info("python dependencies sandbox initialized")

	// start a ticker to update python dependencies to keep the sandbox up-to-date
}


func Run() {
	// init config
	initConfig()
	// init dependencies, it will cost some times
//	go initDependencies()

	initServer()
}

