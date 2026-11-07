/*
StatsD configuration for StoryGen
Aggregates metrics and forwards to backends
*/

{
  // Network settings
  port: 8125,
  mgmt_port: 8126,
  
  // Flush interval in milliseconds
  flushInterval: 10000,
  
  // Percentile thresholds for timers
  percentThreshold: [50, 90, 95, 99],
  
  // Graphite backend configuration
  graphitePort: 2003,
  graphiteHost: "graphite",
  graphite: {
    legacyNamespace: false,
    globalPrefix: "storygen",
    prefixCounter: "counters",
    prefixTimer: "timers",
    prefixGauge: "gauges",
    prefixSet: "sets"
  },
  
  // Backends to load
  backends: ["./backends/graphite", "./backends/console"],
  
  // Console backend for debugging
  console: {
    prettyprint: true
  },
  
  // Delete idle stats
  deleteIdleStats: true,
  deleteGauges: false,
  deleteTimers: true,
  deleteSets: true,
  deleteCounters: true,
  
  // Prefix for all stats
  prefixStats: "statsd",
  
  // Log settings
  log: {
    backend: "stdout",
    application: "statsd",
    level: "INFO"
  },
  
  // Health checks
  healthStatus: "up",
  
  // Histogram settings
  histogram: [
    {
      metric: "storygen.story.duration.*",
      bins: [100, 500, 1000, 2500, 5000, 10000, 30000]
    },
    {
      metric: "storygen.request.duration.*",
      bins: [10, 50, 100, 250, 500, 1000, 5000]
    }
  ],
  
  // Key mappings for metric organization
  keyNameSanitize: false,
  
  // Repeater backend for sending to multiple StatsD servers
  repeater: [
    {
      host: "monitoring-statsd.storygen.internal",
      port: 8125
    }
  ],
  
  // AWS CloudWatch backend
  cloudwatch: {
    namespace: "StoryGen",
    region: "us-east-1",
    dimensions: {
      Environment: process.env.ENVIRONMENT || "dev"
    },
    // Metrics to send to CloudWatch
    whitelist: [
      "storygen.story.*.success",
      "storygen.story.*.failure",
      "storygen.request.*.200",
      "storygen.request.*.500",
      "storygen.error.*"
    ]
  }
}