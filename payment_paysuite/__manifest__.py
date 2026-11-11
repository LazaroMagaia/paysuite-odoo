{
    'name': 'PaySuite Payments',
    'version': '20.0.1.0.0',
    'category': 'Accounting/Payment Providers',
    'summary': 'Accept M-Pesa, e-Mola, mKesh and card payments through PaySuite.',
    'description': """
    Payment provider for PaySuite (Mozambique).

    Requires a PaySuite company account (external service).
    When enabled, the customer's name, email and phone number are sent to
    PaySuite to create or match a contact and process the payment.
    """,
    'author': 'Hypertech, LDA',
    'depends': ['payment'],
    'data': [
        'views/payment_provider_views.xml',
        'data/payment_provider_data.xml',
        'data/payment_method_data.xml',
    ],
    'images': ['static/description/banner.png'],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'application': False,
    'license': 'LGPL-3',
}