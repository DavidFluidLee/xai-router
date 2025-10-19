package gateway

import (
	"fmt"
	"time"

	"github.com/gin-gonic/gin"
)

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
