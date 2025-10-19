package gateway

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
)

// 🔧 新增：获取配置版本信息
func (dr *DistributedRouter) getConfigVersionHandler(c *gin.Context) {
	if !dr.routeManager.redisEnabled {
		c.JSON(503, gin.H{"error": "Redis not available"})
		return
	}

	ctx := c.Request.Context()
	
	// 获取全局版本
	versionStr, err := dr.routeManager.redisClient.Get(ctx, "gateway:config:version").Result()
	if err != nil && err != redis.Nil {
		c.JSON(500, gin.H{"error": err.Error()})
		return
	}

	// 获取更新中的路由
	updatingRoutes, _ := dr.routeManager.redisClient.SMembers(ctx, "gateway:routes:updated").Result()

	// 获取路由总数
	totalRoutes, _ := dr.routeManager.redisClient.HLen(ctx, "gateway:routes").Result()

	response := gin.H{
		"global_version":    versionStr,
		"last_updated":      dr.routeManager.lastConfigUpdate,
		"updating_routes":   updatingRoutes,
		"total_routes":      totalRoutes,
		"memory_routes":     len(dr.routeManager.routeCache),
		"instance_id":       dr.routeManager.instanceID,
		"redis_enabled":     dr.routeManager.redisEnabled,
	}

	c.JSON(200, response)
}

// 扩展的管理接口处理器
func (dr *DistributedRouter) getStreamInfoHandler(c *gin.Context) {
	if !dr.routeManager.redisEnabled {
		c.JSON(503, gin.H{"error": "Redis not available"})
		return
	}

	info, err := dr.routeManager.GetEventStream().GetStreamInfo(c.Request.Context())
	if err != nil {
		c.JSON(500, gin.H{"error": err.Error()})
		return
	}

	c.JSON(200, gin.H{"stream_info": info})
}

func (dr *DistributedRouter) getPendingMessagesHandler(c *gin.Context) {
	if !dr.routeManager.redisEnabled {
		c.JSON(503, gin.H{"error": "Redis not available"})
		return
	}

	consumerGroup := c.Query("consumer_group")
	if consumerGroup == "" {
		consumerGroup = "route-managers"
	}

	pending, err := dr.routeManager.GetEventStream().GetPendingMessages(c.Request.Context(), consumerGroup)
	if err != nil {
		c.JSON(500, gin.H{"error": err.Error()})
		return
	}

	c.JSON(200, gin.H{"pending_messages": pending})
}

func (dr *DistributedRouter) publishTestEventHandler(c *gin.Context) {
	if !dr.routeManager.redisEnabled {
		c.JSON(503, gin.H{"error": "Redis not available"})
		return
	}

	var testEvent struct {
		EventType string      `json:"event_type"`
		RouteID   string      `json:"route_id"`
		RouteData *RouteConfig `json:"route_data"`
	}

	if err := c.BindJSON(&testEvent); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}

	event := &RouteEvent{
		EventID:   fmt.Sprintf("test-%d", time.Now().UnixNano()),
		EventType: testEvent.EventType,
		RouteID:   testEvent.RouteID,
		RouteData: testEvent.RouteData,
		Timestamp: time.Now().Unix(),
		Source:    "test",
	}

	if err := dr.routeManager.GetEventStream().PublishRouteEvent(c.Request.Context(), event); err != nil {
		c.JSON(500, gin.H{"error": err.Error()})
		return
	}

	c.JSON(200, gin.H{"message": "test event published"})
}

// 新增：获取事件消费者状态
func (dr *DistributedRouter) getEventConsumersHandler(c *gin.Context) {
	if !dr.routeManager.redisEnabled {
		c.JSON(503, gin.H{"error": "Redis not available"})
		return
	}

	consumers := make([]map[string]interface{}, 0)
	for _, consumer := range dr.routeManager.eventConsumers {
		consumers = append(consumers, map[string]interface{}{
			"consumer_name":  consumer.config.ConsumerName,
			"consumer_group": consumer.config.ConsumerGroup,
			"running":        consumer.running,
			"batch_size":     consumer.config.BatchSize,
			"block_time":     consumer.config.BlockTime,
		})
	}

	c.JSON(200, gin.H{"consumers": consumers})
}

// 🔧 新增：获取事件处理统计
func (dr *DistributedRouter) getEventStatsHandler(c *gin.Context) {
	if !dr.routeManager.redisEnabled {
		c.JSON(503, gin.H{"error": "Redis not available"})
		return
	}

	ctx := c.Request.Context()
	
	// 获取事件流长度
	streamLen, err := dr.routeManager.redisClient.XLen(ctx, "gateway:events").Result()
	if err != nil {
		c.JSON(500, gin.H{"error": err.Error()})
		return
	}

	// 获取消费者组信息
	groups, err := dr.routeManager.redisClient.XInfoGroups(ctx, "gateway:events").Result()
	if err != nil {
		c.JSON(500, gin.H{"error": err.Error()})
		return
	}

	// 计算待处理消息
	totalPending := int64(0)
	consumerStats := make(map[string]interface{})
	
	for _, group := range groups {
		// 修复：移除未使用的 pending 变量
		_, err := dr.routeManager.redisClient.XPendingExt(ctx, &redis.XPendingExtArgs{
			Stream: "gateway:events",
			Group:  group.Name,
			Start:  "-",
			End:    "+",
			Count:  1000,
		}).Result()
		
		if err == nil {
			consumerStats[group.Name] = gin.H{
				"consumers":    group.Consumers,
				"pending":      group.Pending,
				"last_delivered_id": group.LastDeliveredID,
			}
			totalPending += group.Pending
		}
	}

	response := gin.H{
		"total_events":      streamLen,
		"total_pending":     totalPending,
		"consumer_groups":   consumerStats,
		"instance_id":       dr.routeManager.instanceID,
		"last_config_update": dr.routeManager.lastConfigUpdate,
		"memory_route_count": len(dr.routeManager.routeCache),
	}

	c.JSON(200, response)
}

// 🔧 新增：手动触发配置同步
func (dr *DistributedRouter) triggerSyncHandler(c *gin.Context) {
	if !dr.routeManager.redisEnabled {
		c.JSON(503, gin.H{"error": "Redis not available"})
		return
	}

	// 记录同步开始时间
	startTime := time.Now()
	log.Printf("🔄 [SYNC] 手动触发配置同步 | 实例: %s", dr.routeManager.instanceID)

	// 执行增量加载
	dr.routeManager.loadRoutesIncremental()

	duration := time.Since(startTime)
	log.Printf("✅ [SYNC] 配置同步完成 | 实例: %s | 耗时: %v", dr.routeManager.instanceID, duration)

	c.JSON(200, gin.H{
		"message": "configuration sync triggered",
		"instance_id": dr.routeManager.instanceID,
		"duration_ms": duration.Milliseconds(),
		"sync_time": startTime.Unix(),
	})
}

// 🔧 新增：获取路由详情
func (dr *DistributedRouter) getRouteDetailsHandler(c *gin.Context) {
	routeID := c.Param("routeId")
	
	dr.routeManager.mutex.RLock()
	defer dr.routeManager.mutex.RUnlock()

	route, exists := dr.routeManager.routeCache[routeID]
	if !exists {
		c.JSON(404, gin.H{"error": "route not found"})
		return
	}

	// 从Redis获取路由的原始数据（包含完整信息）
	var redisRoute RouteConfig
	if dr.routeManager.redisEnabled {
		ctx := c.Request.Context()
		routeJSON, err := dr.routeManager.redisClient.HGet(ctx, "gateway:routes", routeID).Result()
		if err == nil {
			json.Unmarshal([]byte(routeJSON), &redisRoute)
		}
	}

	response := gin.H{
		"route": route,
		"redis_data": redisRoute,
		"in_memory": exists,
		"version": dr.routeManager.routeVersions[routeID],
	}

	c.JSON(200, response)
}

// 🔧 新增：清理事件流
func (dr *DistributedRouter) cleanupEventsHandler(c *gin.Context) {
	if !dr.routeManager.redisEnabled {
		c.JSON(503, gin.H{"error": "Redis not available"})
		return
	}

	var request struct {
		MaxAgeHours int `json:"max_age_hours"`
	}
	
	if err := c.BindJSON(&request); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}

	if request.MaxAgeHours <= 0 {
		request.MaxAgeHours = 24 // 默认24小时
	}

	ctx := c.Request.Context()
	cutoffTime := time.Now().Add(-time.Duration(request.MaxAgeHours) * time.Hour)
	cutoffID := fmt.Sprintf("%d", cutoffTime.UnixMilli())

	// 获取旧事件
	messages, err := dr.routeManager.redisClient.XRange(ctx, "gateway:events", "-", cutoffID).Result()
	if err != nil {
		c.JSON(500, gin.H{"error": err.Error()})
		return
	}

	// 删除旧事件
	if len(messages) > 0 {
		var ids []string
		for _, msg := range messages {
			ids = append(ids, msg.ID)
		}
		
		_, err = dr.routeManager.redisClient.XDel(ctx, "gateway:events", ids...).Result()
		if err != nil {
			c.JSON(500, gin.H{"error": err.Error()})
			return
		}
	}

	c.JSON(200, gin.H{
		"message": "events cleanup completed",
		"deleted_count": len(messages),
		"max_age_hours": request.MaxAgeHours,
		"cutoff_time": cutoffTime.Unix(),
	})
}

// 🔧 新增：健康检查端点
func (dr *DistributedRouter) healthCheckHandler(c *gin.Context) {
	healthStatus := gin.H{
		"status":       "healthy",
		"timestamp":    time.Now().Unix(),
		"instance_id":  dr.routeManager.instanceID,
		"redis_enabled": dr.routeManager.redisEnabled,
	}

	if dr.routeManager.redisEnabled {
		ctx, cancel := context.WithTimeout(c.Request.Context(), 2*time.Second)
		defer cancel()
		
		_, err := dr.routeManager.redisClient.Ping(ctx).Result()
		if err != nil {
			healthStatus["status"] = "degraded"
			healthStatus["redis_status"] = "unavailable"
			healthStatus["redis_error"] = err.Error()
		} else {
			healthStatus["redis_status"] = "healthy"
		}
	}

	// 检查内存路由状态
	dr.routeManager.mutex.RLock()
	healthStatus["route_count"] = len(dr.routeManager.routeCache)
	healthStatus["config_version"] = dr.routeManager.lastConfigUpdate
	dr.routeManager.mutex.RUnlock()

	c.JSON(200, healthStatus)
}
