<?php

/**
 * Redis Cache Configuration for AWS ElastiCache - TLS DEFAULT MODE
 * Optimized for CakePHP 4.6+ with native RedisEngine TLS support
 *
 * Environment Variables (.env):
 * REDIS_HOST=master.xxxxx.use1.cache.amazonaws.com
 * REDIS_PORT=6379
 * REDIS_PASSWORD=your-auth-token
 * REDIS_DATABASE=0
 * REDIS_TIMEOUT=10
 * REDIS_PREFIX=myapp_
 * REDIS_PERSISTENT=false  (set true after testing)
 */

use Cake\Cache\Engine\RedisEngine;

// Simplified TLS helper for CakePHP 4.6+
function buildRedisConfig($cacheType, $duration = '+1 hours')
{
    $config = [
        'className' => RedisEngine::class,
        'host' => env('REDIS_HOST', 'localhost'),
        'port' => (int) env('REDIS_PORT', 6379),
        'password' => env('REDIS_PASSWORD'),    // AUTH token
        'database' => (int) env('REDIS_DATABASE', 0),
        'prefix' => env('REDIS_PREFIX', 'cake_') . $cacheType . '_',
        'duration' => $duration,
        'timeout' => (int) env('REDIS_TIMEOUT', 10),
        'read_timeout' => 30,
        'persistent' => filter_var(env('REDIS_PERSISTENT', 'false'), FILTER_VALIDATE_BOOLEAN),
        'compress' => false,
        'serializer' => \Redis::SERIALIZER_PHP,
    ];

    // ✅ Native TLS mode (CakePHP 4.6+)
    if (filter_var(env('REDIS_TLS_ENABLED', 'false'), FILTER_VALIDATE_BOOLEAN)) {
        $config['tls'] = true;
        
        // Optional SSL tweaks for ElastiCache
        $config['ssl'] = [
            'verify_peer' => filter_var(env('REDIS_TLS_VERIFY_PEER', 'false'), FILTER_VALIDATE_BOOLEAN),
            'verify_peer_name' => false,        // ElastiCache hostname mismatch
            'allow_self_signed' => true,
            'SNI_enabled' => true,
        ];
    }

    return $config;
}

return [
    'Cache' => [
        'default' => buildRedisConfig('default', '+1 hours'),
        '_cake_core_' => buildRedisConfig('cake_core', '+1 years'),
        '_cake_model_' => buildRedisConfig('cake_model', '+1 years'),
        '_cake_routes_' => buildRedisConfig('cake_routes', '+1 years'),
        'languages' => buildRedisConfig('languages', '+1 years'),
        'subscription' => buildRedisConfig('subscription', '+1 hours'),
    ],
];

