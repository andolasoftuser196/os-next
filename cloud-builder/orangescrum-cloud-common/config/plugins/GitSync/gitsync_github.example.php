<?php

/**
 * GitHub OAuth Configuration
 *
 * Copy this file to your app's config directory as gitsync_github.php
 * and update with your OAuth credentials
 *
 * SECURITY NOTE:
 * - client_secret and webhook_secret values are automatically encrypted using CakePHP's Security::encrypt()
 * - The encryption uses the application's Security.salt value
 * - Values are decrypted at runtime using GitSync\Utility\ConfigEncryption
 * - When saved via the UI, secrets are stored encrypted in this file
 * - Manual configuration should use plain text; it will be encrypted on first save
 */

return [
    'GitSync' => [
        'github' => [
            'name' => env('GITHUB_CLIENT_NAME', '__GITHUB_NAME__'),
            'client_id' => env('GITHUB_CLIENT_ID', '__GITHUB_CLIENT_ID__'),
            'client_secret' => env('GITHUB_CLIENT_SECRET', '__GITHUB_CLIENT_SECRET__'),
            'redirect_uri' => env('GITHUB_REDIRECT_URI', HTTP_ROOT . 'git-sync/callback/github'),
            'webhook_secret' => env('GITHUB_WEBHOOK_SECRET', '__GITHUB_WEBHOOK_SECRET__'),
        ],
    ],
];
