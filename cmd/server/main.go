package main

import (
	"fmt"
	"log"

	"github.com/langgenius/dify-sandbox/internal/server"
)

func main() {
    fmt.Println("🚀 Starting XAI Router Gateway...")
    
    // 启动服务器
    server.Run()
    
    log.Println("XAI Router Gateway stopped")
}
