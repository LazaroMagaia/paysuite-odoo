{
    'name': 'Payment Provider: PaySuite',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Payment Providers',
    'summary': 'Pagamentos M-Pesa, e-Mola, mKesh e cartão através do PaySuite.',
    'author': 'Hypertech, LDA',
    'depends': ['payment'],
    'data': [
        'views/payment_provider_views.xml',
        'data/payment_provider_data.xml',
        'data/payment_method_data.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'application': False,
    'license': 'LGPL-3',
}