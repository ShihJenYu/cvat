import hashlib

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import ObjectDoesNotExist

class WithIPBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, mysterious_key=None):

        print(username,password,mysterious_key)
        try:
            user = User.objects.get(username=username)
            if user.check_password(password):
                isAdmin = 'admin' in user.groups.values_list('name', flat=True)
                print('isAdmin',isAdmin)
                if isAdmin:
                    return user
                print('is my auth')
                OFFICE_IP = ['114.37.145.43', '220.134.104.253', '114.43.64.62']
                OFFICE_Key = []
                for ip in OFFICE_IP:
                    mhash = hashlib.md5()
                    mhash.update(ip.encode('utf-8'))
                    OFFICE_Key.append(mhash.hexdigest())
                print(OFFICE_Key)

                ip_valid = False
                if username.lower().startswith('oto') and mysterious_key in OFFICE_Key:
                    ip_valid = True
                if (not username.lower().startswith('oto')) and (not mysterious_key in OFFICE_Key):
                    ip_valid = True

                if ip_valid:
                    return user

        except ObjectDoesNotExist:
            pass

        print('not found user')
        return None