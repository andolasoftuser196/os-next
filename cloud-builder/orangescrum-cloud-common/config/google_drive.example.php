<?php
/**
 * Google Drive API Configuration Example
 *
 * Instructions:
 * 1. Go to Google Cloud Console: https://console.cloud.google.com
 * 2. Create/select a project and enable the Google Drive API
 * 3. Create credentials (API key or OAuth 2.0 Client ID as needed)
 * 4. Copy this file to 'google_drive.php' and add your actual API key
 *
 * Environment Variables:
 * You can use environment variables instead of hardcoding:
 * - GOOGLE_DRIVE_API_KEY
 */

return [
    'GoogleDrive' => [
        // Your Google OAuth Client ID
        'api_key' => env('GOOGLE_DRIVE_API_KEY', 'your-api-key-here'),
        
        // Enable/disable Google OAuth globally
        'enabled' => true,
    ],
];
