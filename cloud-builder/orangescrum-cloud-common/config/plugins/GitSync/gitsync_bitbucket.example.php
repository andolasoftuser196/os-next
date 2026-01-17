<?php

/**
 * Bitbucket OAuth Configuration
 *
 * Copy this file to your app's config directory as gitsync_bitbucket.php
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
        'bitbucket' => [
            'name' => env('BITBUCKET_CLIENT_NAME', '__BITBUCKET_NAME__'),
            'client_id' => env('BITBUCKET_CLIENT_ID', '__BITBUCKET_CLIENT_ID__'),
            'client_secret' => env('BITBUCKET_CLIENT_SECRET', '__BITBUCKET_CLIENT_SECRET__'),
            'redirect_uri' => env('BITBUCKET_REDIRECT_URI', HTTP_ROOT . 'git-sync/callback/bitbucket'),
            'webhook_secret' => env('BITBUCKET_WEBHOOK_SECRET', '__BITBUCKET_WEBHOOK_SECRET__'),
        ],
    ],
];
