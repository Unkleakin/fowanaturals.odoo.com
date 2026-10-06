{
    'name': 'Fowa Naturals WooCommerce Connector',
    'version': '20.0.1.0.0',
    'summary': 'Sync products, stock, customers and orders with fowanaturals.com (WooCommerce)',
    'category': 'Sales',
    'depends': ['sale_management', 'stock', 'account'],
    'external_dependencies': {'python': ['requests']},
    'data': [
        'data/cron.xml',
        'views/res_config_settings_views.xml',
        'views/woo_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
