package gateway

// 路由配置
type RouteConfig struct {
	ID          string            `json:"id"`
	Path        string            `json:"path"`
	Method      string            `json:"method"`
	Handler     string            `json:"handler"` // "sandbox", "proxy", "static"
	SandboxType string            `json:"sandbox_type,omitempty"` // "python", "nodejs", "go"
	Code        string            `json:"code,omitempty"`
	Target      string            `json:"target,omitempty"`
	Timeout     int               `json:"timeout,omitempty"`
	Metadata    map[string]string `json:"metadata,omitempty"`
}

// 沙箱服务实例
type SandboxInstance struct {
	ID       string `json:"id"`
	URL      string `json:"url"`
	Type     string `json:"type"`
	Status   string `json:"status"` // "healthy", "unhealthy", "starting"
	Load     int    `json:"load"`   // 当前负载
	LastPing int64  `json:"last_ping"`
}

// 负载均衡器接口
type LoadBalancerInterface interface {
	Select(instances []*SandboxInstance) *SandboxInstance
	SetStrategy(strategy string)
}
