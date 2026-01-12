<?php
/**
 * Queue Configuration for AWS ElastiCache Redis
 * 
 * Updated for TLS + AUTH with phpredis 6.3.0
 * Compatible with CakePHP Queue plugin + ElastiCache encryption
 * 
 * Environment Variables (.env):
 * QUEUE_URL=rediss://:your-auth-token@master.xxxxx.use1.cache.amazonaws.com:6379/1
 * 
 * Test: bin/cake queue worker default
 */

return [
    'Queue' => [
        'default' => [
            // TLS URL format for ElastiCache (rediss:// = Redis + SSL)
            'url' => env('QUEUE_URL', 'rediss://127.0.0.1:6379/1'),
            
            // Default queue name
            'queue' => 'default',
            
            // Log worker output
            'logger' => 'stdout',
            
            // Store failed jobs (requires database table)
            'storeFailedJobs' => true,

            // Wait 10s for new jobs
            'receiveTimeout' => 10000,
            
            // Worker process settings
            'workerPoolSize' => 4,
            'workerTimeout' => 300,
            
            // Redis-specific options (passed to phpredis)
            'options' => [
                'timeout' => (int)env('REDIS_TIMEOUT', 10),
                'read_timeout' => 30,
                'persistent' => filter_var(env('REDIS_PERSISTENT', 'false'), FILTER_VALIDATE_BOOLEAN),
                'ssl' => [  // TLS context for ElastiCache
                    'verify_peer' => false,
                    'verify_peer_name' => false,
                    'allow_self_signed' => true,
                    'SNI_enabled' => true,
                ],
            ],
        ],
    ],
];

