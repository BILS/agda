from django import forms

from .models import AgdaUser


class AgdaUserEditForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        # Call the original __init__ method before assigning
        # field overloads
        super(AgdaUserEditForm, self).__init__(*args, **kwargs)

    class Meta:
        model = AgdaUser
        fields = ("first_name", "last_name",)
