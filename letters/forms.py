from django import forms
from django.contrib.auth.models import User
from .models import SectorProfile, SECTOR_CHOICES, Letter


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
    date_received = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    replied_at = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        required = False,
        label="Replied On (Date & Time)"

    )

    class Meta:
        model = Letter
        # ADDED 'is_replied' and 'replied_at' here
        fields = [
            'serial_number', 'date_received', 'sender_name',
            'letter_type', 'target_sector', 'administrated_by',
            'attachment', 'is_replied', 'replied_at'
        ]
        labels = {
            'serial_number': 'Serial Number',
            'sender_name': 'Sender Name',
            'letter_type': 'Subject / Type',
            'target_sector': 'Assign to Sector',
            'administrated_by': 'Administrated By',
            'attachment': 'Scan/Photo (Optional)',
            'is_replied': 'Mark as Resolved/Replied',
        }