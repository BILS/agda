from django import forms

class SpeciesGeoCoderForm(forms.Form):
    name = forms.CharField(max_length=100, initial='SpeciesGeoCoder job', help_text='Job name')
    localities = forms.FileField(
            help_text='',
            label='Localities', 
            required=True)
    polygons = forms.FileField(
            help_text='',
            label='Polygons', 
            required=True)
    occurences = forms.IntegerField(
            help_text='',
            initial=1,
            required=False,
            min_value=1,
            label='Occurence cutoff')
    verbose = forms.BooleanField(
            help_text='',
            required=False,
            label='Verbose')
    plot = forms.BooleanField(
            help_text='',
            required=False,
            label='Make plots')
