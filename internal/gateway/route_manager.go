package gateway

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/gorilla/mux"
	"github.com/redis/go-redis/v9"
)

// 路由管理器
type RouteManager struct {
	redisClient   *redis.Client
	routeCache    map[string]RouteConfig
	router        *mux.Router
	updateChannel chan struct{}
	mutex         sync.RWMutex
}

func NewRouteManager(redisClient *redis.Client) *RouteManager {
	rm := &RouteManager{
		redisClient:   redisClient,
		routeCache:    make(map[string]RouteConfig),
		router:        mux.NewRouter(),
		updateChannel: make(chan struct{}, 1),
	}

	// 从Redis加载初始配置
	rm.loadRoutesFromRedis()

	// 启动配置监听
	go rm.watchRouteChanges()

	return rm
}

// 关键算法：路由匹配
func (rm *RouteManager) matchRoute(path, method string) *RouteConfig {
	rm.mutex.RLock()
	defer rm.mutex.RUnlock()

	var matchedRoute *RouteConfig
	var matchPriority int

	for _, route := range rm.routeCache {
		priority := rm.calculateMatchPriority(route, path, method)
		if priority > matchPriority {
			matchedRoute = &route
			matchPriority = priority
		}
	}

	return matchedRoute
}

// 计算匹配优先级
func (rm *RouteManager) calculateMatchPriority(route RouteConfig, path, method string) int {
	if route.Method != method && route.Method != "ANY" {
		return 0
	}

	// 1. 精确匹配最高优先级
	if route.Path == path {
		return 100
	}

	// 2. 参数匹配次之 /users/{id}
	if rm.matchPathWithParams(route.Path, path) {
		return 90
	}

	// 3. 前缀匹配 /api/
	if strings.HasPrefix(path, route.Path+"/") {
		return 80
	}

	// 4. 通配符匹配 /api/*
	if strings.Contains(route.Path, "*") {
		pattern := strings.ReplaceAll(route.Path, "*", ".*")
		if matched, _ := regexp.MatchString("^"+pattern+"$", path); matched {
			return 70
		}
	}

	return 0
}

// 匹配带参数的路由
func (rm *RouteManager) matchPathWithParams(routePath, requestPath string) bool {
	route := mux.NewRouter()
	route.Path(routePath).Methods("GET")
	
	req, _ := http.NewRequest("GET", requestPath, nil)
	var match mux.RouteMatch
	return route.Match(req, &match)
}

// 从Redis加载路由配置
func (rm *RouteManager) loadRoutesFromRedis() {
	ctx := context.Background()
	routes, err := rm.redisClient.HGetAll(ctx, "gateway:routes").Result()
	if err != nil {
		log.Printf("Failed to load routes from Redis: %v", err)
		return
	}

	rm.mutex.Lock()
	defer rm.mutex.Unlock()

	for _, routeJSON := range routes {
		var route RouteConfig
		if err := json.Unmarshal([]byte(routeJSON), &route); err == nil {
			rm.routeCache[route.ID] = route
		}
	}

	log.Printf("Loaded %d routes from Redis", len(rm.routeCache))
}

// 监听路由配置变化
func (rm *RouteManager) watchRouteChanges() {
	ticker := time.NewTicker(10 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-rm.updateChannel:
			rm.loadRoutesFromRedis()
		case <-ticker.C:
			// 定期检查配置更新
			rm.checkForUpdates()
		}
	}
}

func (rm *RouteManager) checkForUpdates() {
	ctx := context.Background()
	lastUpdate, err := rm.redisClient.Get(ctx, "gateway:routes:last_updated").Result()
	if err != nil && err != redis.Nil {
		log.Printf("Failed to check route updates: %v", err)
		return
	}

	if lastUpdate != "" {
		// 这里可以比较时间戳来判断是否需要更新
		rm.loadRoutesFromRedis()
	}
}

// 添加路由
func (rm *RouteManager) AddRoute(route RouteConfig) error {
	rm.mutex.Lock()
	defer rm.mutex.Unlock()

	// 验证路由配置
	if err := rm.validateRoute(route); err != nil {
		return err
	}

	// 保存到Redis
	ctx := context.Background()
	routeJSON, _ := json.Marshal(route)
	
	err := rm.redisClient.HSet(ctx, "gateway:routes", route.ID, routeJSON).Err()
	if err != nil {
		return err
	}

	// 更新最后修改时间
	rm.redisClient.Set(ctx, "gateway:routes:last_updated", 
		time.Now().Format(time.RFC3339), 0)

	// 更新内存缓存
	rm.routeCache[route.ID] = route

	// 通知更新
	select {
	case rm.updateChannel <- struct{}{}:
	default:
		// 通道已满，跳过
	}

	return nil
}

// 删除路由
func (rm *RouteManager) DeleteRoute(routeID string) error {
	rm.mutex.Lock()
	defer rm.mutex.Unlock()

	ctx := context.Background()
	
	// 从Redis删除
	err := rm.redisClient.HDel(ctx, "gateway:routes", routeID).Err()
	if err != nil {
		return err
	}

	// 更新最后修改时间
	rm.redisClient.Set(ctx, "gateway:routes:last_updated", 
		time.Now().Format(time.RFC3339), 0)

	// 从内存缓存删除
	delete(rm.routeCache, routeID)

	// 通知更新
	select {
	case rm.updateChannel <- struct{}{}:
	default:
	}

	return nil
}

// 验证路由配置
func (rm *RouteManager) validateRoute(route RouteConfig) error {
	if route.ID == "" {
		return fmt.Errorf("route ID is required")
	}
	if route.Path == "" {
		return fmt.Errorf("route path is required")
	}
	if route.Method == "" {
		return fmt.Errorf("route method is required")
	}
	if route.Handler == "" {
		return fmt.Errorf("route handler is required")
	}

	// 验证处理器类型
	validHandlers := map[string]bool{
		"sandbox": true,
		"proxy":   true,
		"static":  true,
	}
	if !validHandlers[route.Handler] {
		return fmt.Errorf("invalid handler type: %s", route.Handler)
	}

	// 如果是沙箱处理器，验证沙箱类型
	if route.Handler == "sandbox" {
		validSandboxTypes := map[string]bool{
			"python": true,
			"nodejs": true,
			"go":     true,
		}
		if !validSandboxTypes[route.SandboxType] {
			return fmt.Errorf("invalid sandbox type: %s", route.SandboxType)
		}
	}

	return nil
}

// 获取所有路由
func (rm *RouteManager) GetAllRoutes() []RouteConfig {
	rm.mutex.RLock()
	defer rm.mutex.RUnlock()

	routes := make([]RouteConfig, 0, len(rm.routeCache))
	for _, route := range rm.routeCache {
		routes = append(routes, route)
	}
	return routes
}
