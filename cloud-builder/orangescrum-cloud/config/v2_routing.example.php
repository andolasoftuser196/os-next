<?php
/**
 * V2/V4 Routing Configuration
 * 
 * Copy this file to v2_migration.php and update the values
 * 
 * ARCHITECTURE:
 * - V2 login page is the COMMON LOGIN PAGE for both v2 and v4
 * - V2 signup is disabled (new users sign up in v4)
 * - V4 doesn't have its own login screen (uses v2 common login page)
 * - This config enables routing between v2 and v4 during login
 * 
 * This configuration is used by the AutoLoginController to:
 * - Authenticate API requests from the v2 application
 * - Check if users exist in v4 database
 * - Generate auto-login links for v4 users accessing via common login page
 */

return [
    'V2Routing' => [
        /**
         * API Key for v2 application authentication
         * 
         * This key must match the V4_API_KEY in the v2 application
         * Generate a secure random key and keep it secret
         * 
         * Example: openssl rand -base64 32
         */
        'apiKey' => env('V2_ROUTING_API_KEY', 'your-secure-api-key-here-change-this'),
        
        /**
         * Base URL for the V2 application
         * 
         * Used by V4 to check if users exist in V2 before registration
         * Should NOT include trailing slash
         * 
         * Examples:
         * - Production: https://app.ossiba.com
         * - Development: http://localhost
         */
        'baseUrl' => env('V2_BASE_URL', ''),

        /**
         * Base URL for the v4 application
         * 
         * This URL is used when generating auto-login links
         * Should NOT include trailing slash
         * 
         * Examples:
         * - Production: https://v4.ossiba.com
         * - Development: http://localhost:8080
         * - Development with domain: http://v4.ossiba.local
         */
        'v4BaseUrl' => env('V4_BASE_URL', ''),

        /**
         * Auto-login token expiration time (in minutes)
         * Default: 15 minutes
         */
        'tokenExpiration' => env('V2_ROUTING_TOKEN_EXPIRATION', 15),

        /**
         * API request timeout (in seconds)
         * Default: 10 seconds
         */
        'timeout' => env('V2_ROUTING_TIMEOUT', 10),

        /**
         * SSL verification for API requests
         * Set to false only in development environments
         * Default: true (enabled)
         */
        'sslVerify' => filter_var(env('V2_ROUTING_SSL_VERIFY', 'true'), FILTER_VALIDATE_BOOLEAN),

        /**
         * Enable debug logging for routing requests
         * Set to false in production
         */
        'debug' => filter_var(env('DEBUG', 'false'), FILTER_VALIDATE_BOOLEAN),
    ],
    
    'V4Routing' => [
        /**
         * Enable V4 routing (routing users from v4 to v2 common login page)
         * 
         * When enabled:
         * - V4 login page redirects to v2 common login page
         * - V2 login page checks for v4 users and routes them back
         * 
         * When disabled:
         * - V4 runs independently with its own login screen
         * - Use this when v4 is deployed as a standalone application
         */
        'enabled' => filter_var(env('V4_ROUTING_ENABLED', 'false'), FILTER_VALIDATE_BOOLEAN),
        
        /**
         * Base URL for the v2 application (common login page)
         * 
         * This URL is used when redirecting from v4 login to common login
         * Should NOT include trailing slash
         * 
         * Examples:
         * - Production: https://app.yourdomain.com
         * - Local dev: https://app.ossiba.com
         * - Development: http://localhost:8000
         */
        'v2BaseUrl' => env('V2_BASE_URL', ''),
        
        /**
         * Auto-login token expiration time (in minutes)
         * Default: 15 minutes
         */
        'tokenExpiration' => env('V2_ROUTING_TOKEN_EXPIRATION', 15),
        
        /**
         * Enable debug logging for routing requests
         * Set to false in production
         */
        'debug' => filter_var(env('DEBUG', 'false'), FILTER_VALIDATE_BOOLEAN),
    ],
];
