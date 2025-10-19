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
	redisClient    *redis.Client
	eventStream    *EventStreamManager
	routeCache     map[string]RouteConfig
	router         *mux.Router
	updateChannel  chan struct{}
	mutex          sync.RWMutex
	redisEnabled   bool
	eventConsumers []*EventConsumer
}

func NewRouteManager(redisClient *redis.Client) *RouteManager {
	rm := &RouteManager{
		redisClient:   redisClient,
		routeCache:    make(map[string]RouteConfig),
		router:        mux.NewRouter(),
		updateChannel: make(chan struct{}, 1),
		redisEnabled:  true,
	}

	// 测试 Redis 连接
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	
	_, err := redisClient.Ping(ctx).Result()
	if err != nil {
		log.Printf("⚠️  Redis not available, using in-memory storage only")
		rm.redisEnabled = false
	} else {
		// 初始化事件流管理器
		rm.eventStream = NewEventStreamManager(redisClient)
		
		// 从Redis加载初始配置
		rm.loadInitialRoutes()
		
		// 启动事件消费者
		rm.startEventConsumers()
	}

	// 启动配置监听
	go rm.watchConfigurationChanges()

	return rm
}

// 加载初始路由
func (rm *RouteManager) loadInitialRoutes() {
	if !rm.redisEnabled {
		return
	}

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

// 启动事件消费者
func (rm *RouteManager) startEventConsumers() {
	if !rm.redisEnabled {
		return
	}

	// 创建路由事件消费者
	routeHandler := &RouteEventHandler{routeManager: rm}
	consumerConfig := EventConsumerConfig{
		ConsumerGroup: "route-managers",
		ConsumerName:  fmt.Sprintf("consumer-%d", time.Now().UnixNano()),
		BatchSize:     10,
		BlockTime:     5 * time.Second,
		AutoAck:       true,
	}

	consumer, err := rm.eventStream.CreateConsumer(consumerConfig, routeHandler)
	if err != nil {
		log.Printf("Failed to create event consumer: %v", err)
		return
	}

	consumer.Start()
	rm.eventConsumers = append(rm.eventConsumers, consumer)
	log.Printf("✅ Started route event consumer: %s", consumerConfig.ConsumerName)
}

// 路由事件处理器
type RouteEventHandler struct {
	routeManager *RouteManager
}

func (h *RouteEventHandler) HandleEvent(event *RouteEvent) error {
	switch event.EventType {
	case "CREATE":
		return h.handleCreateEvent(event)
	case "UPDATE":
		return h.handleUpdateEvent(event)
	case "DELETE":
		return h.handleDeleteEvent(event)
	default:
		log.Printf("Unknown event type: %s", event.EventType)
		return nil
	}
}

// 同样修复 handleCreateEvent
func (h *RouteEventHandler) handleCreateEvent(event *RouteEvent) error {
    if event.RouteData == nil {
        return fmt.Errorf("missing route data for CREATE event")
    }

    // 🔧 修复：使用 RouteData 中的 ID
    targetRouteID := event.RouteData.ID
    if targetRouteID == "" {
        targetRouteID = event.RouteID
    }

    h.routeManager.mutex.Lock()
    defer h.routeManager.mutex.Unlock()

    h.routeManager.routeCache[targetRouteID] = *event.RouteData
    log.Printf("📝 Created route from event: %s", targetRouteID)
    return nil
}

func (h *RouteEventHandler) handleUpdateEvent(event *RouteEvent) error {
    if event.RouteData == nil {
        return fmt.Errorf("missing route data for UPDATE event")
    }

    // 🔧 修复：使用 RouteData 中的 ID 而不是事件的 RouteID
    targetRouteID := event.RouteData.ID
    if targetRouteID == "" {
        targetRouteID = event.RouteID // 回退到事件RouteID
    }

    h.routeManager.mutex.Lock()
    defer h.routeManager.mutex.Unlock()

    log.Printf("🔄 Processing UPDATE event for route: %s (event ID: %s)", targetRouteID, event.RouteID)
    
    if existing, exists := h.routeManager.routeCache[targetRouteID]; exists {
        log.Printf("📝 Updating existing route: %s", targetRouteID)
        log.Printf("   Old code: %.50s...", existing.Code)
        log.Printf("   New code: %.50s...", event.RouteData.Code)
        
        h.routeManager.routeCache[targetRouteID] = *event.RouteData
        log.Printf("✅ Successfully updated route from event: %s", targetRouteID)
    } else {
        log.Printf("⚠️  Route not found for UPDATE, creating new: %s", targetRouteID)
        h.routeManager.routeCache[targetRouteID] = *event.RouteData
    }
    
    return nil
}

func (h *RouteEventHandler) handleDeleteEvent(event *RouteEvent) error {
    h.routeManager.mutex.Lock()
    defer h.routeManager.mutex.Unlock()

    targetRouteID := event.RouteID
    
    log.Printf("🔄 Processing DELETE event for route: %s", targetRouteID)
    
    if _, exists := h.routeManager.routeCache[targetRouteID]; exists {
        delete(h.routeManager.routeCache, targetRouteID)
        log.Printf("✅ Successfully deleted route from event: %s", targetRouteID)
    } else {
        log.Printf("⚠️  Route not found for DELETE event: %s", targetRouteID)
        // 可以尝试从事件数据中查找路由ID
        if event.RouteData != nil && event.RouteData.ID != "" {
            alternativeID := event.RouteData.ID
            if _, exists := h.routeManager.routeCache[alternativeID]; exists {
                delete(h.routeManager.routeCache, alternativeID)
                log.Printf("✅ Successfully deleted route using alternative ID: %s", alternativeID)
            }
        }
    }
    
    return nil
}

// 监听配置变化
func (rm *RouteManager) watchConfigurationChanges() {
	ticker := time.NewTicker(10 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-rm.updateChannel:
			rm.loadInitialRoutes()
		case <-ticker.C:
			rm.checkForConfigurationUpdates()
		}
	}
}

func (rm *RouteManager) checkForConfigurationUpdates() {
	if !rm.redisEnabled {
		return
	}

	ctx := context.Background()
	lastUpdate, err := rm.redisClient.Get(ctx, "gateway:routes:last_updated").Result()
	if err != nil && err != redis.Nil {
		log.Printf("Failed to check route updates: %v", err)
		return
	}

	if lastUpdate != "" {
		rm.loadInitialRoutes()
	}
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

// 添加路由（发布事件）
func (rm *RouteManager) AddRoute(route RouteConfig) error {
	rm.mutex.Lock()
	defer rm.mutex.Unlock()

	// 验证路由配置
	if err := rm.validateRouteConfiguration(route); err != nil {
		return err
	}

	// 设置时间戳
	now := time.Now().Unix()
	if route.CreatedAt == 0 {
		route.CreatedAt = now
	}
	route.UpdatedAt = now

	// 发布创建事件
	if rm.redisEnabled {
		event := &RouteEvent{
			EventID:   fmt.Sprintf("create-%d", now),
			EventType: "CREATE",
			RouteID:   route.ID,
			RouteData: &route,
			Timestamp: now,
			Source:    "route-manager",
		}

		if err := rm.eventStream.PublishRouteEvent(context.Background(), event); err != nil {
			log.Printf("Failed to publish CREATE event: %v", err)
			// 继续在内存中保存
		}
	}

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

// 更新路由（发布事件）
func (rm *RouteManager) UpdateRoute(routeID string, newRoute RouteConfig) error {
	rm.mutex.Lock()
	defer rm.mutex.Unlock()

	// 检查路由是否存在
	if _, exists := rm.routeCache[routeID]; !exists {
		return fmt.Errorf("route %s not found", routeID)
	}

	// 验证新的路由配置
	if err := rm.validateRouteConfiguration(newRoute); err != nil {
		return err
	}

	// 确保ID一致
	if routeID != newRoute.ID {
		return fmt.Errorf("route ID cannot be changed")
	}

	// 设置更新时间戳
	newRoute.UpdatedAt = time.Now().Unix()

	// 发布更新事件
	if rm.redisEnabled {
		event := &RouteEvent{
			EventID:   fmt.Sprintf("update-%d", time.Now().Unix()),
			EventType: "UPDATE",
			RouteID:   routeID,
			RouteData: &newRoute,
			Timestamp: time.Now().Unix(),
			Source:    "route-manager",
		}

		if err := rm.eventStream.PublishRouteEvent(context.Background(), event); err != nil {
			log.Printf("Failed to publish UPDATE event: %v", err)
			// 继续在内存中更新
		}
	}

	// 更新内存缓存
	rm.routeCache[routeID] = newRoute

	// 通知更新
	select {
	case rm.updateChannel <- struct{}{}:
	default:
	}

	return nil
}

// 删除路由（发布事件）
func (rm *RouteManager) DeleteRoute(routeID string) error {
	rm.mutex.Lock()
	defer rm.mutex.Unlock()

	// 发布删除事件
	if rm.redisEnabled {
		event := &RouteEvent{
			EventID:   fmt.Sprintf("delete-%d", time.Now().Unix()),
			EventType: "DELETE",
			RouteID:   routeID,
			Timestamp: time.Now().Unix(),
			Source:    "route-manager",
		}

		if err := rm.eventStream.PublishRouteEvent(context.Background(), event); err != nil {
			log.Printf("Failed to publish DELETE event: %v", err)
			// 继续删除内存中的路由
		}
	}

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
func (rm *RouteManager) validateRouteConfiguration(route RouteConfig) error {
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

	validHandlers := map[string]bool{
		"sandbox": true,
		"proxy":   true,
		"static":  true,
	}
	if !validHandlers[route.Handler] {
		return fmt.Errorf("invalid handler type: %s", route.Handler)
	}

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

// 获取事件流管理器（用于管理接口）
func (rm *RouteManager) GetEventStream() *EventStreamManager {
	return rm.eventStream
}
