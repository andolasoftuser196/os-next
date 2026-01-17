<?php
/**
 * File Cache Configuration Example
 * 
 * Copy this file to cache_file.php and configure for your environment.
 * 
 * This configuration uses the filesystem to store cache files.
 * File cache is simple and requires no external dependencies, making it ideal
 * for development environments or small applications.
 * 
 * Environment Variables:
 * - CACHE_PREFIX: Cache key prefix (default: 'cake_')
 * - CACHE_MASK: Permissions mask for cache files (default: 0664)
 */

use Cake\Cache\Engine\FileEngine;

return [
    /*
     * Configure the cache adapters.
     */
    'Cache' => [
        'default' => [
            'className' => FileEngine::class,
            'path' => CACHE,
            'prefix' => env('CACHE_PREFIX', 'cake_') . 'default_',
            'url' => env('CACHE_DEFAULT_URL', null),
        ],

        /*
         * Configure the cache used for general framework caching.
         * Translation cache files are stored with this configuration.
         * Duration will be set to '+2 minutes' in bootstrap.php when debug = true
         */
        '_cake_core_' => [
            'className' => FileEngine::class,
            'prefix' => env('CACHE_PREFIX', 'cake_') . 'cake_core_',
            'path' => CACHE . 'persistent' . DS,
            'serialize' => true,
            'duration' => '+1 years',
            'url' => env('CACHE_CAKECORE_URL', null),
        ],

        /*
         * Configure the cache for model and datasource caches.
         * This cache configuration is used to store schema descriptions,
         * and table listings in connections.
         * Duration will be set to '+2 minutes' in bootstrap.php when debug = true
         */
        '_cake_model_' => [
            'className' => FileEngine::class,
            'prefix' => env('CACHE_PREFIX', 'cake_') . 'cake_model_',
            'path' => CACHE . 'models' . DS,
            'serialize' => true,
            'duration' => '+1 years',
            'url' => env('CACHE_CAKEMODEL_URL', null),
        ],

        /*
         * Configure the cache for routes. The cached routes collection is built
         * the first time the routes are processed through `config/routes.php`.
         * Duration will be set to '+2 seconds' in bootstrap.php when debug = true
         */
        '_cake_routes_' => [
            'className' => FileEngine::class,
            'prefix' => env('CACHE_PREFIX', 'cake_') . 'cake_routes_',
            'path' => CACHE,
            'serialize' => true,
            'duration' => '+1 years',
        ],

        /*
         * Configure the cache for language files
         */
        'languages' => [
            'className' => FileEngine::class,
            'prefix' => env('CACHE_PREFIX', 'cake_') . 'languages_',
            'path' => CACHE . 'persistent' . DS,
            'serialize' => true,
            'duration' => '+1 years',
        ],

        /*
         * Subscription cache for storing subscription-related data
         */
        'subscription' => [
            'className' => FileEngine::class,
            'prefix' => env('CACHE_PREFIX', 'cake_') . 'subscription_',
            'path' => CACHE,
            'serialize' => true,
            'duration' => '+1 hours',
        ],
    ],
];
