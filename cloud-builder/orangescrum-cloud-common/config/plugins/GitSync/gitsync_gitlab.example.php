<?php

/**
 * GitLab OAuth Configuration
 *
 * Copy this file to your app's config directory as gitsync_gitlab.php
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
        'gitlab' => [
            'name' => env('GITLAB_CLIENT_NAME', '__GITLAB_NAME__'),
            'client_id' => env('GITLAB_CLIENT_ID', '__GITLAB_CLIENT_ID__'),
            'client_secret' => env('GITLAB_CLIENT_SECRET', '__GITLAB_CLIENT_SECRET__'),
            'redirect_uri' => env('GITLAB_REDIRECT_URI', HTTP_ROOT . 'git-sync/callback/gitlab'),
            'instance_url' => env('GITLAB_INSTANCE_URL', 'https://gitlab.com'),
            'webhook_secret' => env('GITLAB_WEBHOOK_SECRET', '__GITLAB_WEBHOOK_SECRET__'),
        ],
    ],
];
