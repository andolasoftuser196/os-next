<?php

use Cake\Core\Configure;

/**
 * Configuration settings for the GitHub API integration.
 *
 * This array contains the necessary client ID, client secret, and redirect URI
 * for authenticating with the GitHub API. The values are loaded from the
 * environment variables `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, and
 * `GITHUB_REDIRECT_URI` respectively.
 */
return [
    'Github' => [
        'name' => env('GITHUB_CLIENT_NAME', '__GITHUB_CLIENT_NAME__'),
        'client_id' => env('GITHUB_CLIENT_ID', '__GITHUB_CLIENT_ID__'),
        'client_secret' => env('GITHUB_CLIENT_SECRET', '__GITHUB_CLIENT_SECRET__'),
        'redirect_uri' => env('GITHUB_REDIRECT_URI', HTTP_ROOT .'git/gitconnect'),
        'hook_url' => env('GITHUB_HOOK_URI', HTTP_ROOT .'githooks/updategithubevents'),
    ]
];
