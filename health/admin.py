from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(User)
admin.site.register(Appointment)
admin.site.register(Prescription)
admin.site.register(Insurance)
admin.site.register(EmergencyContact)
admin.site.register(Hospital)
admin.site.register(Subscription)
admin.site.register(Contact)
