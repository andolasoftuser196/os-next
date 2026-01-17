<?php
/**
 * Google OAuth 2.0 Configuration
 * 
 * Setup Instructions:
 * 1. Go to Google Cloud Console: https://console.cloud.google.com
 * 2. Create a new project or select an existing one
 * 3. Enable the Google+ API
 * 4. Go to Credentials → Create Credentials → OAuth 2.0 Client ID
 * 5. Configure authorized redirect URIs for all your domains:
 *    - https://app.yourdomain.com/oauth/google/callback
 *    - https://*.yourdomain.com/oauth/google/callback (for tenant subdomains)
 * 6. Copy this file to 'google_oauth.php' and add your actual credentials
 * 
 * Environment Variables:
 * You can also use environment variables instead of hardcoding:
 * - GOOGLE_OAUTH_CLIENT_ID
 * - GOOGLE_OAUTH_CLIENT_SECRET
 * - GOOGLE_OAUTH_REDIRECT_URI
 */

return [
    'GoogleOAuth' => [
        // Your Google OAuth Client ID
        'client_id' => env('GOOGLE_OAUTH_CLIENT_ID'),
        
        // Your Google OAuth Client Secret
        'client_secret' => env('GOOGLE_OAUTH_CLIENT_SECRET'),
        
        // OAuth redirect URI (must match Google Cloud Console configuration)
        'redirect_uri' => env('GOOGLE_OAUTH_REDIRECT_URI'),
        
        // OAuth scopes to request from Google
        'scopes' => [
            'openid',
            'email',
            'profile',
        ],
        
        // Enable/disable Google OAuth globally
        'enabled' => filter_var(env('GOOGLE_OAUTH_ENABLED', 'false'), FILTER_VALIDATE_BOOLEAN),
    ],
];
