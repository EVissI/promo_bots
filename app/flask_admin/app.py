import asyncio

from app.config import setup_logger
logger = setup_logger("admin_panel")
from flask import Flask
from flask_admin import Admin,AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import SecureForm
from app.db.database import sync_session
from app.db.models import User,Promocode
from app.flask_admin.model_views import UserView,PromoView


app = Flask(__name__)

app.config['SECRET_KEY'] = 'AJKClasc6x5z1i2S3Kx3zcdo23'
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'

class MyAdminIndexView(AdminIndexView):
    form_base_class = SecureForm
    def is_visible(self):
        return False

admin = Admin(app, name='promo', template_mode='bootstrap4',index_view=MyAdminIndexView())


admin.add_view(UserView(User, sync_session,name = 'Юзеры'))
admin.add_view(PromoView(Promocode, sync_session,name = 'Промокоды'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)