<?php
/**
 * Google reCAPTCHA Configuration
 * 
 * Get your reCAPTCHA keys from: https://www.google.com/recaptcha/admin
 * 
 * Copy this file to 'recaptcha.php' and add your actual keys
 */

return [
    'Recaptcha' => [
        // Your reCAPTCHA Site Key (for frontend)
        'siteKey' => env('RECAPTCHA_SITE_KEY'),
        
        // Your reCAPTCHA Secret Key (for backend validation)
        'secretKey' => env('RECAPTCHA_SECRET_KEY'),
        
        // Version: 'v2' for checkbox, 'v3' for invisible
        'version' => env('RECAPTCHA_VERSION', 'v3'),
        
        // Enable/disable reCAPTCHA globally
        'enabled' => filter_var(env('RECAPTCHA_ENABLED', 'false'), FILTER_VALIDATE_BOOLEAN),
        
        // Minimum score for v3 (0.0 - 1.0, lower is more likely a bot)
        'minScore' => (float)env('RECAPTCHA_MIN_SCORE', '0.5'),
        
        // Theme: 'light' or 'dark'
        'theme' => env('RECAPTCHA_THEME', 'light'),
        
        // Size: 'normal' or 'compact'
        'size' => env('RECAPTCHA_SIZE', 'normal'),
    ],
];
