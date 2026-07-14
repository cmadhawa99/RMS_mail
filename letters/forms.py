from random import choices

from django import forms
from django.contrib.auth.models import User
from .models import SectorProfile, SECTOR_CHOICES, Letter, OFFICER_CHOICES


class UserForm(forms.ModelForm):
    sector = forms.ChoiceField(choices=SECTOR_CHOICES, required=False, label="Assigned Sector")

    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'id': 'id_new_password'}),
        required=False,
        label="Password",
        help_text="Leave blank to keep the current password (only required for new users)."
    )


    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name']

    def __init__(self, *args, **kwargs):
        user = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        if user:
            if hasattr(user, 'sectorprofile'):
                self.fields['sector'].initial = user.sectorprofile.sector

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('new_password')

        if not self.instance.pk and not password:
            self.add_error('new_password', "Password is required for new accounts.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        password = self.cleaned_data.get('new_password')
        if password:
            user.set_password(password)

        user.is_staff = False
        user.is_superuser = False

        if commit:
            user.save()
            sector_val = self.cleaned_data.get('sector')
            SectorProfile.objects.update_or_create(user=user, defaults={'sector': sector_val})
        return user



class LetterForm(forms.ModelForm):
    date_received = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
    )

    replied_at = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required = False,
        label="Reply Date"

    )

    administrated_by = forms.ChoiceField(
        choices=OFFICER_CHOICES,
        required=False,
        label="Administrated By"
    )

    accepting_officer_id = forms.CharField(
        required=False,
        label="Accepting Officer ID"
    )

    class Meta:
        model = Letter
        # ADDED 'is_replied' and 'replied_at' here
        fields = [
            'serial_number', 'date_received', 'sender_details',
            'letter_type', 'target_sector', 'administrated_by',
            'accepting_officer_id', 'status', 'replied_at',
            'attachment_1', 'attachment_2', 'attachment_3', 'attachment_4',
            'attachment_5', 'attachment_6'
        ]
        labels = {
            'serial_number': 'Serial Number',
            'sender_details': 'Sender Details (Name, Org, Address)',
            'letter_type': 'Subject / Type',
            'target_sector': 'Assign to Sector',
            'administrated_by': 'Administrated By',
            'accepting_officer_id': 'Accepting Officer ID',
            'status': 'Letter Status',
            'attachment_1': 'Attachment 1',
            'attachment_2': 'Attachment 2',
            'attachment_3': 'Attachment 3',
            'attachment_4': 'Attachment 4',
            'attachment_5': 'Attachment 5',
            'attachment_6': 'Attachment 6'
        }

        widgets = {
            'sender_details': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Enter full sender name, organization, and address details...'}),
            'letter_type': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter Subject Description'}),
        }

    # - - NEW SECURITY CHECK - -

    def clean_serial_number(self):
        serial_number = self.cleaned_data.get('serial_number')

        if self.instance.pk:
            if self.instance.serial_number != serial_number:
                if Letter.objects.filter(serial_number=serial_number).exists():
                    raise forms.ValidationError(f"Serial Number '{serial_number}' already exists. You cannot overwrite it.")

        else:
            if Letter.objects.filter(serial_number=serial_number).exists():
                raise forms.ValidationError(f"Serial Number '{serial_number}' is already in use.")

        return serial_number


class UserLetterForm(forms.ModelForm):

    replied_at = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        label="Reply Date"
    )

    accepting_officer_id = forms.CharField(
        required=False,
        label="Accepting Officer ID"
    )


    class Meta:
        model = Letter
        fields = [
            'serial_number', 'date_received', 'sender_details',
            'letter_type', 'target_sector', 'administrated_by',
            'accepting_officer_id', 'status', 'replied_at',
            'attachment_1', 'attachment_2', 'attachment_3', 'attachment_4',
            'attachment_5', 'attachment_6'
        ]

        labels = {
            'serial_number': 'Serial Number',
            'sender_details': 'Sender Details',
            'letter_type': 'Subject / Type',
            'replied_at': 'Reply Date',
            'status': 'Letter Status',
        }
        widgets = {
            'sender_details': forms.Textarea(attrs={'rows': 3}),
            'letter_type': forms.Textarea(attrs={'rows': 2}),
            'date_received': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['status'].choices = [
            ('PENDING', 'Pending'),
            ('REPLIED', 'Replied'),
            ('NOT_REQUIRED', 'Not Required'),
        ]

        compulsory_fields = ['serial_number', 'date_received', 'sender_details', 'letter_type', 'accepting_officer_id']
        for field in compulsory_fields:
            self.fields[field].required = True

        non_compulsory = ['replied_at', 'administrated_by', 'status']
        for field in non_compulsory:
            self.fields[field].required = False

        if self.instance and self.instance.pk:
            fields_to_lock = ['serial_number', 'date_received', 'sender_details', 'letter_type', 'administrated_by', 'accepting_officer_id']
            for field_name in fields_to_lock:
                val = getattr(self.instance, field_name)
                if val:
                    self.fields[field_name].widget.attrs['readonly'] = True
                    self.fields[field_name].widget.attrs[
                        'style'] = 'pointer-events: none; opacity: 0.6; background-color: rgba(156, 163, 175, 0.2);'


    def clean_serial_number(self):
        serial_number = self.cleaned_data.get('serial_number')

        if self.instance and self.instance.pk:
            if str(self.instance.serial_number) != str(serial_number):
                raise forms.ValidationError(
                    "Security Alert: You cannot modify the serial number of an existing record.")


        else:
            if Letter.objects.filter(serial_number=serial_number).exists():
                raise forms.ValidationError(f"Serial Number '{serial_number}' already exists in the system.")


        return serial_number


    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        replied_at = cleaned_data.get('replied_at')

        if status == 'REPLIED' and not replied_at:
            self.add_error('replied_at', "Reply Date is compulsory when marking a letter as 'Replied'.")

        if status == 'NOT_REQUIRED':
            cleaned_data['replied_at'] = None

        return cleaned_data