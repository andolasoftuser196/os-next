<?php
/**
 * Cloud Storage Configuration (Example)
 * 
 * Copy this file to cloudstorage.php and fill in your credentials.
 * The cloudstorage.php file should be added to .gitignore
 * 
 * Supported Providers:
 * - Google Drive
 * - Dropbox
 * - OneDrive
 */

return [
    'CloudStorage' => [
        'auth_domain' => env('CLOUD_STORAGE_AUTH_DOMAIN', 'app.osdurango.com'),
        /**
         * ============================================
         * GOOGLE DRIVE CONFIGURATION
         * ============================================
         * 
         * Setup Instructions:
         * 1. Go to https://console.cloud.google.com/
         * 2. Create a new project or select existing one
         * 3. Enable the following APIs:
         *    - Google Drive API
         *    - Google Picker API
         * 4. Create OAuth 2.0 credentials:
         *    - Go to "Credentials" → "Create Credentials" → "OAuth client ID"
         *    - Application type: Web application
         *    - Name: Your App Name
         *    - Authorized JavaScript origins:
         *      * https://yourdomain.com
         *    - Authorized redirect URIs:
         *      * https://yourdomain.com/cloud-storage/callback/google_drive
         * 5. Create an API Key:
         *    - Go to "Credentials" → "Create Credentials" → "API Key"
         *    - Restrict key to Google Picker API
         * 6. Copy the credentials below
         */
        'GoogleDrive' => [
            // OAuth 2.0 Client ID
            // Example: 123456789012-abcdefghijklmnop.apps.googleusercontent.com
            'client_id' => '',
            
            // OAuth 2.0 Client Secret
            // Example: GOCSPX-AbCdEfGhIjKlMnOpQrStUvWx
            'client_secret' => '',
            
            // API Key for Picker
            // Example: AIzaSyAaBbCcDdEeFfGgHhIiJjKkLl
            'api_key' => '',
            
            // Numeric part of client ID (auto-extracted if empty)
            // Example: 123456789012
            'client_id_num' => '',
            
            // Enable/disable Google Drive
            'enabled' => true,
            
            // OAuth Scopes
            'scopes' => [
                'https://www.googleapis.com/auth/drive.file',
                'https://www.googleapis.com/auth/drive.readonly',
                'https://www.googleapis.com/auth/userinfo.email',
                'https://www.googleapis.com/auth/userinfo.profile',
            ],
        ],

        /**
         * ============================================
         * DROPBOX CONFIGURATION
         * ============================================
         * 
         * Setup Instructions:
         * 1. Go to https://www.dropbox.com/developers/apps
         * 2. Click "Create app"
         * 3. Choose API: Scoped access
         * 4. Choose access type: Full Dropbox
         * 5. Name your app
         * 6. In the Settings tab:
         *    - Add Redirect URIs:
         *      * https://yourdomain.com/cloud-storage/callback/dropbox
         * 7. In the Permissions tab, enable:
         *    - files.metadata.read
         *    - files.content.read
         *    - sharing.read
         * 8. Copy App key and App secret below
         */
        'Dropbox' => [
            // App Key (Client ID)
            // Example: abcdefghijk1234
            'client_id' => '',
            
            // App Secret (Client Secret)
            // Example: abcdefghijklmnop
            'client_secret' => '',
            
            // Enable/disable Dropbox
            'enabled' => true,
            
            // OAuth Scopes (automatically requested)
            'scopes' => [
                'files.metadata.read',
                'files.content.read',
                'sharing.read',
            ],
        ],

        /**
         * ============================================
         * ONEDRIVE CONFIGURATION
         * ============================================
         * 
         * Setup Instructions:
         * 1. Go to https://portal.azure.com/
         * 2. Navigate to "Azure Active Directory" → "App registrations"
         * 3. Click "New registration"
         * 4. Fill in:
         *    - Name: Your App Name
         *    - Supported account types: Choose based on your needs
         *      * Accounts in any organizational directory and personal Microsoft accounts
         * 5. Redirect URI:
         *    - Platform: Web
         *    - URI: https://yourdomain.com/cloud-storage/callback/onedrive
         * 6. After creation, go to "Certificates & secrets":
         *    - Create a new client secret
         *    - Copy the VALUE (not the Secret ID)
         * 7. Go to "API permissions":
         *    - Add Microsoft Graph permissions:
         *      * Files.Read (Delegated)
         *      * Files.Read.All (Delegated)
         *      * User.Read (Delegated)
         *      * offline_access (Delegated)
         *    - Grant admin consent (if required)
         * 8. Copy Application (client) ID and secret below
         */
        'OneDrive' => [
            // Application (client) ID
            // Example: 12345678-1234-1234-1234-123456789abc
            'client_id' => '',
            
            // Client Secret (VALUE from "Certificates & secrets")
            // Example: AbC~dEf1GhI2jKl3MnO4pQr5StU6vWx7yZ
            'client_secret' => '',
            
            // Tenant ID
            // Use 'common' for multi-tenant (personal + work accounts)
            // Use 'consumers' for personal accounts only
            // Use 'organizations' for work/school accounts only
            // Use specific tenant ID for single tenant
            'tenant_id' => 'common',
            
            // Enable/disable OneDrive
            'enabled' => true,
            
            // OAuth Scopes
            'scopes' => [
                'Files.Read',
                'Files.Read.All',
                'User.Read',
                'offline_access',
            ],
        ],

        /**
         * ============================================
         * GLOBAL SETTINGS
         * ============================================
         */
        'Settings' => [
            // Token expiry buffer in seconds (refresh tokens before they expire)
            'token_buffer' => 300, // 5 minutes
            
            // Auto-sync files metadata interval in hours
            'auto_sync_interval' => 24, // 1 day
            
            // Enable debug mode (logs API calls and errors)
            'debug' => false,
            
            // Maximum files allowed per selection
            'max_files_per_selection' => 50,
            
            // Enable file thumbnails
            'enable_thumbnails' => true,
            
            // Thumbnail size: 'small', 'medium', 'large'
            'thumbnail_size' => 'medium',
            
            // Maximum file size for preview in bytes (10 MB)
            'max_preview_size' => 10485760,
            
            // Allowed file extensions (empty array = allow all)
            'allowed_extensions' => [
                // Documents
                'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
                'odt', 'ods', 'odp', 'txt', 'rtf', 'csv',
                
                // Images
                'jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp',
                
                // Archives
                'zip', 'rar', '7z', 'tar', 'gz',
                
                // Media
                'mp4', 'avi', 'mov', 'wmv', 'mp3', 'wav',
            ],
            
            // Block file extensions (overrides allowed_extensions)
            'blocked_extensions' => [
                'exe', 'bat', 'cmd', 'sh', 'ps1',
            ],
        ],

        /**
         * ============================================
         * FEATURE FLAGS
         * ============================================
         */
        'Features' => [
            // Allow users to select files from multiple providers at once
            'multi_provider_selection' => true,
            
            // Enable file preview in browser
            'file_preview' => true,
            
            // Enable direct file download
            'file_download' => true,
            
            // Enable file sharing links
            'file_sharing' => true,
            
            // Enable automatic metadata sync from cloud
            'auto_sync' => true,
            
            // Log all file attachment activities
            'activity_logging' => true,
            
            // Cache file metadata
            'metadata_caching' => true,
            
            // Cache duration in minutes
            'cache_duration' => 60,
        ],

        /**
         * ============================================
         * SECURITY SETTINGS
         * ============================================
         */
        'Security' => [
            // Encrypt access tokens in database (recommended)
            'encrypt_tokens' => true,
            
            // Encryption key (leave empty to use Security.salt from app.php)
            'encryption_key' => '',
            
            // Require HTTPS for OAuth callbacks (disable only for local development)
            'require_ssl' => true,
            
            // Allowed IP addresses for API access (empty = allow all)
            // Example: ['192.168.1.1', '10.0.0.0/8']
            'ip_whitelist' => [],
            
            // Rate limiting per user (requests per minute)
            'rate_limit' => 60,
            
            // Token rotation: Force re-authentication after X days
            'force_reauth_days' => 90,
        ],
    ],
];
