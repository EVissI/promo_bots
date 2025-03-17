from flask_admin.contrib.sqla import ModelView
import flask
from flask import redirect, url_for
from wtforms.fields import DateField
from flask_admin.form import DatePickerWidget
from datetime import datetime

class AuthModelView(ModelView):
    def is_accessible(self):
        return flask.session.get('logged_in')

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

class UserView(AuthModelView):
    can_create = False
    can_delete = False
    edit_modal = True
    column_list = ['telegram_id', 'username', 'subscription_end', 'role', 'is_blocked']

    form_overrides = {
        'subscription_end': DateField
    }
    form_args = {
        'subscription_end': {
            'widget': DatePickerWidget(),
            'format': '%d-%m-%Y'
        }
    }
    column_formatters = {
        'subscription_end': lambda v, c, m, p: m.subscription_end.strftime('%d-%m-%Y') if m.subscription_end else ''
    }
    
    column_searchable_list = ['telegram_id','username']
    column_filters = ['role', 'is_blocked']
    column_editable_list = ['role', 'is_blocked']
    form_widget_args = {
        'telegram_id': {'readonly': True},
        'username': {'readonly': True},
        'promo_code': {'readonly': True},
        'subscription_end': {'readonly': True}
    }

class PromoView(AuthModelView):
    can_create = True
    can_delete = True
    edit_modal = True
    
    column_list = ['promo_name', 'duration', 'usage_limit', 'used_count']
    column_searchable_list = ['promo_name']
    column_filters = ['duration', 'usage_limit']
    column_editable_list = ['duration', 'usage_limit']
    
    form_widget_args = {
        'used_count': {'readonly': True}
    }
    form_excluded_columns = ['created_at', 'updated_at', 'used_count']
    column_descriptions = {
        'duration': 'Длительность в днях',
        'usage_limit': 'Лимит на использование',
        'used_count': 'Кол-во использований'
    }
    
    column_default_sort = 'promo_name'

    def on_model_change(self, form, model, is_created):
        if is_created:
            model.used_count = 0