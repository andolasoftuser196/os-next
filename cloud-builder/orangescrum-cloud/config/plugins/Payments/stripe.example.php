<?php

return [
    'Stripe' => [
        // We use env() so we can set these in docker-compose or .env files
        'publishable_key' => env('STRIPE_PUBLISHABLE_KEY', null),
        'secret_key'      => env('STRIPE_SECRET_KEY', null),
        'webhook_secret'  => env('STRIPE_WEBHOOK_SECRET', null),

        // Optional: Default currency or other Stripe-specific settings
        'currency'        => env('STRIPE_CURRENCY', 'usd'),
        'product_prefix'  => 'cloud_v3_',
    ],
];
