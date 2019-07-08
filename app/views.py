from django.shortcuts import render, redirect, get_object_or_404
from django.utils import dateparse
from django.core.exceptions import PermissionDenied
from django.contrib.admin.models import LogEntry
from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.db.models import Max
from . import form_utilities
from .form_utilities import *
from . import checks
from .models import *
import datetime
import json
import time


def login_view(request):
    """
    Presents a simple form for logging in a user.
    If requested via POST, looks for the username and password,
    and attempts to log the user in. If the credentials are invalid,
    it passes an error message to the context which the template will
    render using a Bootstrap alert.

    :param request: The Django request object.
    :return: The rendered 'login' page.
    """
    context = {'navbar': 'login'}
    if request.POST:
        user, message = login_user_from_form(request, request.POST)
        if user:
            return redirect('health:home')
        elif message:
            context['error_message'] = message
    return render(request, 'login.html', context)


def login_user_from_form(request, body):
    """
    Validates a user's login credentials and returns a tuple
    containing either a valid, logged-in user or a failure
    message.

    Checks if all fields were supplied, then attempts to authenticate,
    then checks if the 'remember' checkbox was checked. If it was, sets
    the cookie's expiration to 0, meaning it will be invalidated when the
    session ends.

    :param request: The Django request object.
    :return: The rendered 'login' page.
    """
    email = body.get("email")
    password = body.get("password")
    if not all([email, password]):
        return None, "You must provide an email and password."
    email = email.lower()  # all emails are lowercase in the database.
    user = authenticate(username=email, password=password)
    remember = body.get("remember")
    if user is None:
        return None, "Invalid username or password."
    login(request, user)
    if remember is not None:
        request.session.set_expiry(0)
    return user, None


def logout_view(request):
    """
    Logs the user out and redirects the user to the login page.
    :param request: The Django request.
    :return: A 301 redirect to the login page.
    """
    logout(request)
    return redirect('health:home1')


def handle_prescription_form(request, body, prescription=None):
    name = body.get("name")
    dosage = body.get("dosage")
    patient = body.get("patient")
    directions = body.get("directions")
    if not all([name, dosage, patient, directions]):
        return None, "All fields are required."
    try:
        patient = User.objects.get(pk=int(patient))
    except ValueError:
        return None, "We could not find the user specified."

    if prescription:
        changed_fields = []
        if prescription.name != name:
            changed_fields.append('name')
            prescription.name = name
        if prescription.dosage != dosage:
            changed_fields.append('dosage')
            prescription.dosage = dosage
        if prescription.directions != directions:
            changed_fields.append('directions')
            prescription.directions = directions
        if prescription.patient != patient:
            changed_fields.append('patient')
            prescription.patient = patient
        prescription.save()
        change(request, prescription, changed_fields)
    else:
        prescription = Prescription.objects.create(name=name, dosage=dosage,
                                                   patient=patient, directions=directions,
                                                   prescribed=timezone.now(), active=True)

        if not prescription:
            return None, "We could not create that prescription. Please try again."
        addition(request, prescription)
    return prescription, None


@login_required
def prescriptions(request, error=None):
    """
    Renders a table of the prescriptions associated with this user.

    :param request: The Django request.
    :return: A rendered version of prescriptions.html
    """
    context = {
        "navbar": "prescriptions",
        "logged_in_user": request.user,
        "prescriptions": request.user.prescription_set.filter(active=True).all()
    }
    if error:
        context["error_message"] = error

    return render(request, 'prescriptions.html', context)


def add_prescription_form(request):
    return prescription_form(request, None)


def prescription_form(request, prescription_id):
    prescription = None
    if prescription_id:
        prescription = get_object_or_404(Prescription, pk=prescription_id)
    if request.POST:
        if not request.user.can_add_prescription():
            raise PermissionDenied
        p, message = handle_prescription_form(request, request.POST, prescription)
        return prescriptions(request, error=message)
    context = {
        'prescription': prescription,
        'logged_in_user': request.user
    }
    return render(request, 'edit_prescription.html', context)


def delete_prescription(request, prescription_id):
    p = get_object_or_404(Prescription, pk=prescription_id)
    p.active = False
    p.save()
    deletion(request, p, repr(p))
    return redirect('health:prescriptions')


def signup(request):
    """
    Presents a simple signup page with a form of all the required
    fields for new users.
    Uses the full_signup_context function to populate a year/month/day picker
    and, if the user was created successfully, prompts the user to log in.
    :param request:
    :return:
    """
    context = full_signup_context(None)
    context['is_signup'] = True
    if request.POST:
        user, message = handle_user_form(request, request.POST)
        if user:
            addition(request, user)
            if request.user.is_authenticated():
                return redirect('health:signup')
            else:
                return redirect('health:login')
        elif message:
            context['error_message'] = message
    context['navbar'] = 'signup'
    return render(request, 'signup.html', context)


def full_signup_context(user):
    """
    Returns a dictionary containing valid years, months, days, hospitals,
    and groups in the database.
    """
    return {
        "year_range": reversed(range(1900, datetime.date.today().year + 1)),
        "day_range": range(1, 32),
        "months": [
            "Jan", "Feb", "Mar", "Apr",
            "May", "Jun", "Jul", "Aug",
            "Sep", "Oct", "Nov", "Dec"
        ],
        "hospitals": Hospital.objects.all(),
        "groups": Group.objects.all(),
        "sexes": MedicalInformation.SEX_CHOICES,
        "user_sex_other": (user and user.medical_information and
                           user.medical_information.sex not in MedicalInformation.SEX_CHOICES)
    }


@login_required
def add_group(request):
    message = None
    if request.POST:
        group, message = handle_add_group_form(request, request.POST)
        if group:
            addition(request, group)
            return redirect('health:conversation', group.pk)
    return messages(request, error=message)


def handle_add_group_form(request, body):
    name = body.get('name')
    recipient_ids = body.getlist('recipient')
    message = body.get('message')

    if not all([name, recipient_ids, message]):
        return None, "All fields are required."
    if not [r for r in recipient_ids if r.isdigit()]:
        return None, "Invalid recipient."
    group = MessageGroup.objects.create(
        name=name
    )
    try:
        ids = [int(r) for r in recipient_ids]
        recipients = User.objects.filter(pk__in=ids)
    except User.DoesNotExist:
        return None, "Could not find user."
    group.members.add(request.user)
    for r in recipients:
        group.members.add(r)
    group.save()
    Message.objects.create(sender=request.user, body=message,
                           group=group, date=timezone.now())
    return group, None


@login_required
def my_medical_information(request):
    """
    Gets the primary key of the current user and redirects to the medical_information view
    for the logged-in user.
    :param request:
    :return:
    """
    return medical_information(request, request.user.pk)


@login_required
def medical_information(request, user_id):
    """
    Checks if the logged-in user has permission to modify the requested user.
    If not, raises a PermissionDenied which Django catches by redirecting to
    a 403 page.

    If requested via GET:
        Renders a page containing all the user's fields pre-filled-in
        with their information.
    If requested via POST:
        modifies the values and redirects to the same page, with the new values.
    :param request: The Django request.
    :param user_id: The user id being requested. This is part of the URL:
    /users/<user_id>/
    :return:
    """
    requested_user = get_object_or_404(User, pk=user_id)
    is_editing_own_medical_information = requested_user == request.user
    if not is_editing_own_medical_information and not\
            request.user.can_edit_user(requested_user):
        raise PermissionDenied

    context = full_signup_context(requested_user)

    if request.POST:
        user, message = handle_user_form(request, request.POST, user=requested_user)
        if user:
            return redirect('health:medical_information', user.pk)
        elif message:
            context['error_message'] = message

    context["requested_user"] = requested_user
    context["user"] = request.user
    context["requested_hospital"] = requested_user.hospital()
    context['is_signup'] = False
    context["navbar"] = "my_medical_information" if is_editing_own_medical_information else "medical_information"
    return render(request, 'medical_information.html', context)


def handle_user_form(request, body, user=None):
    """
    Creates a user and validates all of the fields, in turn.
    If there is a failure in any validation, the returned tuple contains
    None and a failure message.
    If validation succeeds and the user can be created, then the returned tuple
    contains the user and None for a failure message.
    :param body: The POST body from the request.
    :return: A tuple containing the User if successfully created,
             or a failure message if the operation failed.
    """
    password = body.get("password")
    first_name = body.get("first_name")
    last_name = body.get("last_name")

    email = body.get("email")
    group = body.get("group")
    patient_group = Group.objects.get(name='Patient')
    group = Group.objects.get(pk=int(group)) if group else patient_group
    is_patient = group == patient_group
    phone = form_utilities.sanitize_phone(body.get("phone_number"))
    month = int(body.get("month"))
    day = int(body.get("day"))
    year = int(body.get("year"))
    date = datetime.date(month=month, day=day, year=year)
    hospital_key = body.get("hospital")
    hospital = Hospital.objects.get(pk=int(hospital_key)) if hospital_key else None
    policy = body.get("policy")
    company = body.get("company")
    sex = body.get("sex")
    other_sex = body.get("other_sex")
    validated_sex = sex if sex in MedicalInformation.SEX_CHOICES else other_sex
    medications = body.get("medications")
    allergies = body.get("allergies")
    medical_conditions = body.get("medical_conditions")
    family_history = body.get("family_history")
    additional_info = body.get("additional_info")
    pic = body.get("pic")
    if not all([first_name, last_name, email, phone,
                month, day, year, date]):
        return None, "All fields are required."
    email = email.lower()  # lowercase the email before adding it to the db.
    if not form_utilities.email_is_valid(email):
        return None, "Invalid email."
    if (user and user.is_patient() and not user.is_superuser) and not all([company, policy]):
        return None, "Insurance information is required."
    if user:
        user.email = email
        user.phone_number = phone
        user.first_name = first_name
        user.last_name = last_name
        user.date_of_birth = date
        if is_patient and user.medical_information is not None:
            user.medical_information.sex = validated_sex
            user.medical_information.medical_conditions = medical_conditions
            user.medical_information.family_history = family_history
            user.medical_information.additional_info = additional_info
            user.medical_information.allergies = allergies
            user.medical_information.medications = medications
            if user.medical_information.insurance:
                user.medical_information.insurance.policy_number = policy
                user.medical_information.insurance.company = company
                user.medical_information.insurance.save()
            else:
                user.medical_information.insurance = Insurance.objects.create(
                    policy_number=policy,
                    company=company
                )
                addition(request, user.medical_information.insurance)
            user.medical_information.save()
            change(request, user.medical_information, 'Changed fields.')
        elif user.is_patient():
            insurance = Insurance.objects.create(policy_number=policy,
                                                 company=company)
            addition(request, insurance)
            medical_information = MedicalInformation.objects.create(
                allergies=allergies, family_history=family_history,
                sex=validated_sex, medications=medications,
                additional_info=additional_info, insurance=insurance,
                medical_conditions=medical_conditions
            )
            addition(request, user.medical_information)
            user.medical_information = medical_information
        if (hospital and
            not HospitalStay.objects.filter(patient=user, hospital=hospital,
                                            discharge__isnull=True).exists()):
            hospital.admit(user)
        if user.is_superuser:
            if not user.groups.filter(pk=group.pk).exists():
                for user_group in user.groups.all():
                    user_group.user_set.remove(user)
                    user_group.save()
                group.user_set.add(user)
                group.save()
        user.save()
        change(request, user, 'Changed fields.')
        return user, None
    else:
        if User.objects.filter(email=email).exists():
            return None, "A user with that email already exists."
        insurance = Insurance.objects.create(policy_number=policy,
                                             company=company)
        if not insurance:
            return None, "We could not create that user. Please try again."
        medical_information = MedicalInformation.objects.create(
            allergies=allergies, family_history=family_history,
            sex=sex, medications=medications,
            additional_info=additional_info, insurance=insurance,
            medical_conditions=medical_conditions
        )
        user = User.objects.create_user(email, email=email,thumbnail=pic,
                                        password=password, date_of_birth=date, phone_number=phone,
                                        first_name=first_name, last_name=last_name,
                                        medical_information=medical_information)
        if user is None:
            return None, "We could not create that user. Please try again."
        hospital.admit(user)
        request.user = user
        addition(request, user)
        addition(request, medical_information)
        addition(request, insurance)
        group.user_set.add(user)
        return user, None


@login_required
def messages(request, error=None):
    other_groups = ['Patient', 'Doctor', 'Nurse']
    if not request.user.is_superuser:
        other_groups.remove(request.user.groups.first().name)
    recipients = (User.objects.filter(groups__name__in=other_groups))
    message_groups = request.user.messagegroup_set\
                            .annotate(max_date=Max('messages__date'))\
                            .order_by('-max_date').all()
    for group in message_groups:
        for message in group.messages.all():
            if request.user not in message.read_members.all():
                group.has_unread = True
                break
    context = {
        'navbar': 'messages',
        'user': request.user,
        'recipients': recipients,
        'groups': message_groups,
        'error_message': error
    }
    return render(request, 'messages.html', context)


def users(request):

    hospital = request.user.hospital()
    doctors = hospital.users_in_group('Doctor')
    patients = hospital.users_in_group('Patient')
    nurses = hospital.users_in_group('Nurse')
    context = {
        'navbar': 'users',
        'doctors': doctors,
        'nurses': nurses,
        'patients': patients
    }
    return render(request, 'users.html', context)


@login_required
def conversation(request, id):
    group = get_object_or_404(MessageGroup, pk=id)
    context = {
        "user": request.user,
        "group": group,
        "message_names": group.combined_names(full=True)
    }
    if request.POST:
        message = request.POST.get('message')
        if message:
            msg = Message.objects.create(sender=request.user, group=group,
                                         body=message, date=timezone.now())
            group.messages.add(msg)
            group.save()
            # redirect to avoid the issues with reloading
            # sending the message again.
            return redirect('health:conversation', group.pk)
    for message in group.messages.all():
        if request.user not in message.read_members.all():
            message.read_members.add(request.user)
            message.save()

    return render(request, 'conversation.html', context)


def handle_appointment_form(request, body, user, appointment=None):
    """
    Validates the provided fields for an appointment request and creates one
    if all fields are valid.
    :param body: The HTTP form body containing the fields.
    :param user: The user intending to create the appointment.
    :return: A tuple containing either a valid appointment or failure message.
    """
    date_string = body.get("date")
    try:
        parsed = dateparse.parse_datetime(date_string)
        if not parsed:
            return None, "Invalid date or time."
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    except:
        return None, "Invalid date or time."
    duration = int(body.get("duration"))
    doctor_id = int(body.get("doctor", user.pk))
    doctor = User.objects.get(pk=doctor_id)
    patient_id = int(body.get("patient", user.pk))
    patient = User.objects.get(pk=patient_id)

    is_change = appointment is not None

    changed = []
    if is_change:
        if appointment.date != parsed:
            changed.append('date')
        if appointment.patient != patient:
            changed.append('patient')
        if appointment.duration != duration:
            changed.append('duration')
        if appointment.doctor != doctor:
            changed.append('doctor')
        appointment.delete()
    if not doctor.is_free(parsed, duration):
        return None, "The doctor is not free at that time." +\
                     " Please specify a different time."

    if not patient.is_free(parsed, duration):
        return None, "The patient is not free at that time." +\
                     " Please specify a different time."
    appointment = Appointment.objects.create(date=parsed, duration=duration,
                                             doctor=doctor, patient=patient)

    if is_change:
        change(request, appointment, changed)
    else:
        addition(request, appointment)
    if not appointment:
        return None, "We could not create the appointment. Please try again."
    return appointment, None


@login_required
def appointment_form(request, appointment_id):
    appointment = None
    if appointment_id:
        appointment = get_object_or_404(Appointment, pk=appointment_id)
    if request.POST:
        appointment, message = handle_appointment_form(
            request, request.POST,
            request.user, appointment=appointment
        )
        return schedule(request, error=message)
    hospital = request.user.hospital()
    context = {
        "user": request.user,
        'appointment': appointment,
        "doctors": hospital.users_in_group('Doctor'),
        "patients": hospital.users_in_group('Patient')
    }
    return render(request, 'edit_appointment.html', context)


@login_required
def schedule(request, error=None):
    """
    Renders a page with an HTML form allowing the user to add an appointment
    with an existing doctor.
    Also shows a table of the existing appointments for the logged-in user.
    """
    now = timezone.now()
    hospital = request.user.hospital()
    context = {
        "navbar": "schedule",
        "user": request.user,
        "doctors": hospital.users_in_group('Doctor'),
        "patients": hospital.users_in_group('Patient'),
        "schedule_future": request.user.schedule()
                                       .filter(date__gte=now)
                                       .order_by('date'),
        "schedule_past": request.user.schedule()
                                     .filter(date__lt=now)
                                     .order_by('-date')
    }
    if error:
        context['error_message'] = error
    return render(request, 'schedule.html', context)


@login_required
def add_appointment_form(request):
    return appointment_form(request, None)


@login_required
def delete_appointment(request, appointment_id):
    a = get_object_or_404(Appointment, pk=appointment_id)
    a.delete()
    return redirect('health:schedule')


@login_required
@user_passes_test(checks.admin_check)
def logs(request):
    group_count = MessageGroup.objects.count()
    average_count = 0
    message_count = Message.objects.count()
    hospital = request.user.hospital()
    if group_count > 0 and message_count > 0:
        average_count = float(message_count) / float(group_count)
    stays = HospitalStay.objects.filter(discharge__isnull=False)
    average_stay = 0.0
    if stays:
        for stay in stays:
            average_stay += float((stay.discharge - stay.admission).total_seconds())
        average_stay /= len(stays)
    average_stay_formatted = time.strftime('%H:%M:%S', time.gmtime(average_stay))
    context = {
        "navbar": "logs",
        "user": request.user,
        "logs": LogEntry.objects.all().order_by('-action_time'),
        "stats": {
            "user_count": HospitalStay.objects.filter(hospital=hospital, discharge__isnull=True).count(),
            "stay_count": HospitalStay.objects.filter(hospital=hospital).count(),
            "discharge_count": HospitalStay.objects.filter(hospital=hospital, discharge__isnull=False).count(),
            "average_stay": average_stay_formatted,
            "patient_count": HospitalStay.objects.filter(hospital=hospital, patient__groups__name='Patient').distinct().count(),
            "doctor_count": HospitalStay.objects.filter(hospital=hospital, patient__groups__name='Doctor').distinct().count(),
            "nurse_count": HospitalStay.objects.filter(hospital=hospital, patient__groups__name='Nurse').distinct().count(),
            "admin_count": User.objects.filter(is_superuser=True).count(),
            "prescription_count": Prescription.objects.count(),
            "active_prescription_count": Prescription.objects.filter(active=True).count(),
            "expired_prescription_count": Prescription.objects.filter(active=False).count(),
            "appointment_count": Appointment.objects.count(),
            "upcoming_appointment_count": Appointment.objects.filter(date__gte=timezone.now()).count(),
            "past_appointment_count": Appointment.objects.filter(date__lt=timezone.now()).count(),
            "conversation_count": group_count,
            "average_message_count": average_count,
            "message_count": message_count
        }
    }
    return render(request, 'logs.html', context)


def home1(request):
    user = User.objects.all()
    context = {
        'user':user
    }
    if request.method =="POST": 
        if 'subs' in request.POST: 
            email = request.POST["contact"]
            sub = Subscription()
            sub.email = email
            sub.save()
        else:
            fname = request.POST["first_name"]
            lname = request.POST["last_name"]
            email = request.POST["email"]
            phone = request.POST["phone"]
            messages = request.POST["message"]
            new_message = Contact()
            new_message.first_name=fname
            new_message.last_name=lname
            new_message.email=email
            new_message.phone=phone
            new_message.message=messages
            new_message.save()

    return render(request, 'index1.html',context)


@login_required
def home(request):
    context = {
        'navbar': 'home',
        'user': request.user,
        'unread_count': request.user.unread_message_count()
    }
    return render(request, 'home.html', context)


@login_required
def export_me(request):
    return export(request, request.user.pk)


@login_required
def export(request, id):
    user = get_object_or_404(User, pk=id)
    if user != request.user and not request.user.is_superuser:
        raise PermissionDenied
    json_object = json.dumps(user.json_object(), sort_keys=True,
                             indent=4, separators=(',', ': '))
    return HttpResponse(json_object,
                        content_type='application/force-download')
