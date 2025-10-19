package static

import (
	"sync"
)

// App配置
type AppConfig struct {
	Port  int    `yaml:"port"`
	Debug bool   `yaml:"debug"`
	Key   string `yaml:"key"`
}

// 代理配置
type ProxyConfig struct {
	Socks5 string `yaml:"socks5"`
	Http   string `yaml:"http"`
	Https  string `yaml:"https"`
}

// 网关配置
type GatewayConfig struct {
	Port                 int    `yaml:"port"`
	RedisAddr            string `yaml:"redis_addr"`
	LoadBalancerStrategy string `yaml:"load_balancer_strategy"`
	HealthCheckInterval  int    `yaml:"health_check_interval"`
	CorsEnabled          bool   `yaml:"cors_enabled"`
}

// Redis配置
type RedisConfig struct {
	Addr     string `yaml:"addr"`
	Password string `yaml:"password"`
	DB       int    `yaml:"db"`
}

type DifySandboxGlobalConfigurations struct {
	App            AppConfig     `yaml:"app"`
	MaxWorkers     int           `yaml:"max_workers"`
	MaxRequests    int           `yaml:"max_requests"`
	WorkerTimeout  int           `yaml:"worker_timeout"`
	PythonPath     string        `yaml:"python_path"`
	EnableNetwork  bool          `yaml:"enable_network"`
	EnablePreload  bool          `yaml:"enable_preload"`
	AllowedSyscalls []string     `yaml:"allowed_syscalls"`
	Proxy          ProxyConfig   `yaml:"proxy"`
	Gateway        GatewayConfig `yaml:"gateway"`
	Redis          RedisConfig   `yaml:"redis"`
}

var (
	globalConfig *DifySandboxGlobalConfigurations
	configMutex  sync.RWMutex
)

func InitConfig(configPath string) error {
	// 这里实现配置加载逻辑
	// 为了简化，我们创建一个默认配置
	globalConfig = &DifySandboxGlobalConfigurations{
		App: AppConfig{
			Port:  8194,
			Debug: true,
			Key:   "dify-sandbox",
		},
		MaxWorkers:     4,
		MaxRequests:    50,
		WorkerTimeout:  5,
		PythonPath:     "/usr/local/bin/python3",
		EnableNetwork:  true,
		EnablePreload:  false,
		AllowedSyscalls: []string{},
		Proxy: ProxyConfig{
			Socks5: "",
			Http:   "",
			Https:  "",
		},
		Gateway: GatewayConfig{
			Port:                 8080,
			RedisAddr:           "localhost:6379",
			LoadBalancerStrategy: "least-connections",
			HealthCheckInterval:  15,
			CorsEnabled:          true,
		},
		Redis: RedisConfig{
			Addr:     "localhost:6379",
			Password: "",
			DB:       0,
		},
	}
	return nil
}

func GetDifySandboxGlobalConfigurations() *DifySandboxGlobalConfigurations {
	configMutex.RLock()
	defer configMutex.RUnlock()
	return globalConfig
}
