# -*- coding: utf-8 -*-

{
    'name': 'Lunch',
    'sequence': 300,
    'version': '1.0',
    'depends': ['mail'],
    'category': 'Human Resources/Lunch',
    'summary': 'Handle lunch orders of your employees',
    'description': """
The base module to manage lunch.
================================

Many companies order sandwiches, pizzas and other, from usual vendors, for their employees to offer them more facilities.

However lunches management within the company requires proper administration especially when the number of employees or vendors is important.

The “Lunch Order” module has been developed to make this management easier but also to offer employees more tools and usability.

In addition to a full meal and vendor management, this module offers the possibility to display warning and provides quick order selection based on employee’s preferences.

If you want to save your employees' time and avoid them to always have coins in their pockets, this module is essential.
    """,
    'data': [
        'security/lunch_security.xml',
        'security/ir.model.access.csv',
        'report/lunch_cashmove_report_views.xml',
        'views/lunch_templates.xml',
        'views/lunch_alert_views.xml',
        'views/lunch_cashmove_views.xml',
        'views/lunch_location_views.xml',
        'views/lunch_orders_views.xml',
        'views/lunch_product_views.xml',
        'views/lunch_supplier_views.xml',
        'views/res_config_settings.xml',
        'views/lunch_views.xml',
        'data/mail_template_data.xml',
        'data/lunch_data.xml',
    ],
    'demo': ['data/lunch_demo.xml'],
    'installable': True,
    'application': True,
    'certificate': '001292377792581874189',
    'assets': {
        'web.assets_backend': [
            'lunch/static/src/scss/lunch_view.scss',
            'lunch/static/src/scss/lunch_kanban.scss',
            'lunch/static/src/scss/lunch_list.scss',
            'lunch/static/src/js/lunch_controller_common.js',
            'lunch/static/src/js/lunch_widget.js',
            'lunch/static/src/js/lunch_mobile.js',
            'lunch/static/src/js/lunch_payment_dialog.js',
            'lunch/static/src/js/lunch_kanban_view.js',
            'lunch/static/src/js/lunch_kanban_controller.js',
            'lunch/static/src/js/lunch_kanban_renderer.js',
            'lunch/static/src/js/lunch_kanban_record.js',
            'lunch/static/src/js/lunch_model_extension.js',
            'lunch/static/src/js/lunch_list_view.js',
            'lunch/static/src/js/lunch_list_controller.js',
            'lunch/static/src/js/lunch_list_renderer.js',
        ],
        'web.qunit_suite_tests': [
            'lunch/static/tests/lunch_test_utils.js',
            'lunch/static/tests/lunch_kanban_tests.js',
            'lunch/static/tests/lunch_list_tests.js',
        ],
        'web.qunit_mobile_suite_tests': [
            'lunch/static/tests/lunch_test_utils.js',
            'lunch/static/tests/lunch_kanban_mobile_tests.js',
        ],
        'web.assets_qweb': [
            'lunch/static/src/xml/lunch_templates.xml',
        ],
    },
    'license': 'LGPL-3',
}
