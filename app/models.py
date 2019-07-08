from django.db import models
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import AbstractUser, Group


class Insurance(models.Model):
    policy_number = models.CharField(max_length=200)
    company = models.CharField(max_length=200)

    def __repr__(self):
        return "{0} with {1}".format(self.policy_number, self.company)

    def __str__(self):
        return "{0} with {1}".format(self.policy_number, self.company)


class EmergencyContact(models.Model):
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)
    phone_number = models.CharField(max_length=30)
    relationship = models.CharField(max_length=30)

    def json_object(self):
        return {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone_number': self.phone_number,
            'relationship': self.relationship,
        }

    def __str__(self):
        return "{0} is {1} of him/her".format(self.first_name, self.relationship)


class MedicalInformation(models.Model):
    SEX_CHOICES = (
        'Female',
        'Male',
        'Intersex',
    )
    sex = models.CharField(max_length=50)
    insurance = models.ForeignKey(Insurance)
    medications = models.CharField(max_length=200, null=True)
    allergies = models.CharField(max_length=200, null=True)
    medical_conditions = models.CharField(max_length=200, null=True)
    family_history = models.CharField(max_length=200, null=True)
    additional_info = models.CharField(max_length=400, null=True)

    def json_object(self):
        return {
            'sex': self.sex,
            'insurance': {
                'company': self.insurance.company,
                'policy_number':
                    self.insurance.policy_number
            },
            'medications': self.medications,
            'allergies': self.allergies,
            'medical_conditions':
                self.medical_conditions,
            'family_history': self.family_history,
            'additional_info': self.additional_info,
        }

    def __repr__(self):
        return (("Sex: {0}, Insurance: {1}, Medications: {2}, Allergies: {3}, " +
                 "Medical Conditions: {4}, Family History: {5}," +
                 " Additional Info: {6}").format(
            self.sex, repr(self.insurance), self.medications,
            self.allergies, self.medical_conditions,
            self.family_history, self.additional_info
        ))

    def __str__(self):
        return "{0} is {1} of him/her".format(self.sex, self.insurance)


class Hospital(models.Model):
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    city = models.CharField(max_length=200)
    state = models.CharField(max_length=30)
    zipcode = models.CharField(max_length=20)

    def json_object(self):
        return {
            'name': self.name,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zipcode': self.zipcode,
        }

    def __repr__(self):
        # "St. Jude Hospital at 1 Hospital Road, Waterbury, CT 06470"
        return ("%s at %s, %s, %s %s" % self.name, self.address, self.city,
                self.state, self.zipcode)

    def __str__(self):
        return "{0} with {1}".format(self.name, self.address)

    def admit(self, user):
        current_hospital_query = HospitalStay.objects.filter(patient=user,
                                                             discharge__isnull=True)
        if current_hospital_query.exists():
            for stay in current_hospital_query.all():
                stay.discharge = timezone.now()
                stay.save()
        HospitalStay.objects.create(patient=user, admission=timezone.now(),
                                    hospital=self)

    def discharge(self, user):
        user_query = HospitalStay.objects.filter(patient=user,
                                                 hospital=self)
        if user_query.exists():
            stay = user_query.first()
            stay.discharge = timezone.now()
            stay.save()

    def users_in_group(self, group_name):
        return list({stay.patient for stay in
                     HospitalStay.objects
                     .filter(hospital=self, patient__groups__name=group_name)
                     .distinct()
                     .order_by('patient__first_name', 'patient__last_name')
                     .all()})


class User(AbstractUser):
    date_of_birth = models.DateField()
    phone_number = models.CharField(max_length=30)
    medical_information = models.ForeignKey(MedicalInformation, null=True)
    emergency_contact = models.ForeignKey(EmergencyContact, null=True)
    thumbnail = models.URLField(null=True, blank=True)

    REQUIRED_FIELDS = ['date_of_birth', 'phone_number', 'email', 'first_name',
                       'last_name']

    def __str__(self):
        return " {0}".format(self.first_name)

    def all_patients(self):
        """
        Returns all patients relevant for a given user.
        If the user is a doctor:
            Returns all patients with active appointments with the doctor.
        If the user is a patient:
            Returns themself.
        If the user is an admin:
            Returns all patients in the database.
        :return:
        """
        if self.is_superuser or self.is_doctor():
            # Admins and doctors can see all users as patients.
            return Group.objects.get(name='Patient').user_set.all()
        elif self.is_nurse():
            # Nurses get all users inside their hospital.
            return Group.objects.get(name='Patient').user_set.filter(hospital=self.hospital)
        else:
            # Users can only see themselves.
            return User.objects.filter(pk=self.pk)

    def can_edit_user(self, user):
        return user == self      \
            or self.is_superuser \
            or user.is_patient() \
            and self.is_doctor() or (self.is_nurse()
                                     and self.hospital == user.hospital)

    def active_patients(self):
        """
        Same as all_patients, but only patients that are active.
        :return: All active patients relevant to the current user.
        """
        return self.all_patients().filter(is_active=True)

    def can_add_prescription(self):
        return self.is_superuser or self.is_doctor()

    def latest_messages(self):
        return self.sent_messages.order_by('-date')

    def unread_message_count(self):
        return Message.objects.filter(group__members__pk=self.pk)\
                              .exclude(read_members__pk=self.pk)\
                              .distinct().count()

    def schedule(self):
        """
        :return: All appointments for which this person is needed.
        """
        if self.is_superuser:
            return Appointment.objects
        elif self.is_doctor():
            # Doctors see all appointments for which they are needed.
            return Appointment.objects.filter(doctor=self)
        # Patients see all appointments
        return Appointment.objects.filter(patient=self)

    def upcoming_appointments(self):
        date = timezone.now()
        start_week = date - timedelta(date.weekday())
        end_week = start_week + timedelta(7)
        return self.schedule().filter(date__range=[start_week, end_week])

    def is_patient(self):
        """
        :return: True if the user belongs to the Patient group.
        """
        return self.is_in_group("Patient")

    def is_nurse(self):
        """
        :return: True if the user belongs to the Nurse group.
        """
        return self.is_in_group("Nurse")

    def is_doctor(self):
        """
        :return: True if the user belongs to the Doctor group.
        """
        return self.is_in_group("Doctor")

    def is_in_group(self, group_name):
        """
        :param group_name: The group within which to check membership.
        :return: True if the user is a member of the group provided.
        """
        try:
            return (Group.objects.get(name=group_name)
                         .user_set.filter(pk=self.pk).exists())
        except ValueError:
            return False

    def group(self):
        return self.groups.first()

    def is_free(self, date, duration):
        """
        Checks the user's schedule for a given date and duration to see if
        the user does not have an appointment at that time.
        :param date:
        :param duration:
        :return:
        """
        schedule = self.schedule().all()
        end = date + timedelta(minutes=duration)
        for appointment in schedule:
            # If the dates intersect (meaning one starts while the other is
            # in progress) then the person is not free at the provided date
            # and time.
            if (date <= appointment.date <= end or
                    appointment.date <= date <= appointment.end()):
                return False
        return True

    def active_prescriptions(self):
        return self.prescription_set.filter(active=True).all()

    def json_object(self):
        json = {
            'name': self.get_full_name(),
            'email': self.email,
            'date_of_birth': self.date_of_birth.isoformat(),
            'phone_number': self.phone_number,
        }
        if self.hospital:
            json['hospital'] = self.hospital().json_object()
        if self.medical_information:
            json['medical_information'] = self.medical_information.json_object()
        if self.emergency_contact:
            json['emergency_contact'] = self.emergency_contact.json_object()
        if self.prescription_set.all():
            json['prescriptions'] = [p.json_object() for p in
                                     self.prescription_set.all()]
        if self.schedule():
            json['appointments'] = [a.json_object()
                                    for a in self.schedule().all()]
        return json

    def hospital(self):
        patient_query = HospitalStay.objects.filter(patient=self,
                                                    discharge__isnull=True)
        if patient_query.exists():
            stays = [x for x in patient_query.all()]
            return stays[0].hospital
        return None


class Appointment(models.Model):
    patient = models.ForeignKey(User, related_name='patient_appointments')
    doctor = models.ForeignKey(User, related_name='doctor_appointments')
    date = models.DateTimeField()
    duration = models.IntegerField()

    def json_object(self):
        return {
            'date': self.date.isoformat(),
            'end': self.end().isoformat(),
            'patient': self.patient.get_full_name(),
            'doctor': self.doctor.get_full_name(),
        }

    def end(self):
        """
        :return: A datetime representing the end of the appointment.
        """
        return self.date + timedelta(minutes=self.duration)

    def __repr__(self):
        return '{0} minutes on {1}, {2} with {3}'.format(self.duration, self.date,
                                                         self.patient, self.doctor)

    def __str__(self):
        return " {0} appionment with {1}".format(self.patient, self.doctor)


class HospitalStay(models.Model):
    patient = models.ForeignKey(User)
    admission = models.DateTimeField()
    discharge = models.DateTimeField(null=True)
    hospital = models.ForeignKey(Hospital)

    def __str__(self):
        return "{0} stay in  {1}".format(self.patient, self.hospital)


class Prescription(models.Model):
    patient = models.ForeignKey(User)
    name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=200)
    directions = models.CharField(max_length=1000)
    prescribed = models.DateTimeField()
    active = models.BooleanField()

    def json_object(self):
        return {
            'name': self.name,
            'dosage': self.dosage,
            'directions': self.directions,
            'prescribed': self.prescribed.isoformat(),
            'active': self.active
        }

    def __repr__(self):
        return '{0} of {1}: {2}'.format(self.dosage, self.name, self.directions)

    def __str__(self):
        return "{0} for {1}".format(self.name, self.patient)


class MessageGroup(models.Model):
    name = models.CharField(max_length=140)
    members = models.ManyToManyField(User)

    def latest_message(self):
        if self.messages.count() == 0:
            return None
        return self.messages.order_by('-date').first()

    def combined_names(self, full=False):
        names_count = self.members.count()
        extras = names_count - 3
        members = self.members.all()
        if not full:
            members = members[:3]
        names = ", ".join([m.get_full_name() for m in members])
        if extras > 0 and not full:
            names += " and %d other%s" % (extras, "" if extras == 1 else "s")
        return names


class Message(models.Model):
    sender = models.ForeignKey(User, related_name='sent_messages')
    group = models.ForeignKey(MessageGroup, related_name='messages')
    body = models.TextField()
    date = models.DateTimeField()
    read_members = models.ManyToManyField(User, related_name='read_messages')

    def preview_text(self):
        return (self.body[:100] + "...") if len(self.body) > 100 else self.body


class Subscription(models.Model):

    email = models.CharField(max_length=200)

    def __str__(self):
        """Unicode representation of Subscription."""
        return self.email


class Contact(models.Model):

    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    email = models.CharField(max_length=200)
    phone = models.IntegerField(null=True, blank=True)
    message = models.TextField()

    def __str__(self):
        """Unicode representation of Subscription."""
        return "{0} for {1}".format(self.first_name, self.last_name)
